"""RAG Service — 임베딩, 청킹, 벡터 인덱싱, 질의응답."""

import asyncio
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.model_router import ModelRouter

logger = get_logger(__name__)


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """텍스트를 청크 단위로 분할합니다 (FR-I01).

    RecursiveCharacterTextSplitter 사용, 한국어 구분자 포함.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    cs = chunk_size or settings.chunking_chunk_size
    co = overlap or settings.chunking_chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cs,
        chunk_overlap=co,
        separators=["\n\n", "\n", "。", ".", "！", "？", "!", "?", " ", ""],
    )
    return splitter.split_text(text)


def _sync_embed(model, texts: list[str]) -> list[list[float]]:
    """sentence-transformers 동기 임베딩 (run_in_executor용)."""
    return model.encode(
        texts,
        batch_size=settings.embedding_batch_size,
        show_progress_bar=False,
    ).tolist()


class RagService:
    """RAG 파이프라인 서비스 (FR-I01~I04, FR-A01~A03)."""

    def __init__(self, db: AsyncSession, router: ModelRouter):
        self._db = db
        self._router = router
        self._embedding_model = None
        self._qdrant = None

    def _get_embedding_model(self):
        """sentence-transformers 모델 지연 로드."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(settings.embedding_model)
        return self._embedding_model

    def _get_qdrant(self):
        """Qdrant 클라이언트 지연 로드."""
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                prefer_grpc=False,  # REST 강제 — gRPC protobuf EnumTypeWrapper 버그 회피
            )
        return self._qdrant

    async def chunk_document(self, doc: Document) -> list[Chunk]:
        """문서를 청크로 분할하고 DB에 저장합니다 (TC-I01)."""
        if not doc.normalized_text:
            return []

        texts = chunk_text(doc.normalized_text)
        chunks = []

        for i, text in enumerate(texts):
            chunk = Chunk(
                doc_id=doc.doc_id,
                version_no=doc.current_version,
                chunk_index=i,
                chunk_text=text,
                token_count=len(text.split()),  # 간략 추정
                embedding_status="pending",
            )
            self._db.add(chunk)
            chunks.append(chunk)

        return chunks

    async def embed_chunks(self, chunks: list[Chunk]) -> int:
        """청크에 임베딩을 생성하고 Qdrant에 저장합니다 (TC-I02, FR-I02).

        Returns:
            성공적으로 임베딩된 청크 수
        """
        if not chunks:
            return 0

        texts = [c.chunk_text for c in chunks]
        loop = asyncio.get_event_loop()
        model = self._get_embedding_model()

        try:
            vectors = await loop.run_in_executor(None, _sync_embed, model, texts)
        except Exception as e:
            logger.error("임베딩 생성 실패", error=str(e))
            for chunk in chunks:
                chunk.embedding_status = "failed"
            return 0

        qdrant = self._get_qdrant()
        from qdrant_client.models import PointStruct
        import uuid as uuid_mod

        points = []
        for chunk, vector in zip(chunks, vectors):
            point_id = str(uuid_mod.uuid4())
            chunk.qdrant_point_id = point_id
            chunk.embedding_model = settings.embedding_model
            chunk.embedding_status = "done"

            points.append(PointStruct(
                id=point_id,
                vector=vector,  # _sync_embed이 이미 .tolist() 반환
                payload={
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.chunk_text[:500],
                },
            ))

        try:
            qdrant.upsert(
                collection_name=settings.qdrant_collection,
                points=points,
            )
        except Exception as e:
            logger.error("Qdrant upsert 실패", error=str(e))
            for chunk in chunks:
                chunk.embedding_status = "failed"
            return 0

        logger.info("임베딩 완료", count=len(chunks))
        return len(chunks)

    async def query(
        self,
        question: str,
        topic_ids: Optional[list[str]] = None,
        top_k: int = 5,
        model_id: Optional[str] = None,
    ) -> dict:
        """자연어 질의에 대한 RAG 답변을 생성합니다 (TC-I03, FR-A01~A03)."""
        # 1. 질의 임베딩
        loop = asyncio.get_event_loop()
        model = self._get_embedding_model()
        query_vector = (await loop.run_in_executor(
            None, lambda: model.encode([question]).tolist()
        ))[0]

        # 2. Qdrant 벡터 검색
        qdrant = self._get_qdrant()
        filter_condition = None
        if topic_ids:
            from qdrant_client.models import Filter, FieldCondition, MatchAny
            filter_condition = Filter(
                must=[FieldCondition(key="doc_id", match=MatchAny(any=topic_ids))]
            )

        search_results = qdrant.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=filter_condition,
            with_payload=True,
        )

        # 3. 청크 텍스트 조합
        chunk_texts = [r.payload.get("chunk_text", "") for r in search_results]
        doc_ids = list({r.payload.get("doc_id", "") for r in search_results})

        # 4. 출처 문서 조회
        stmt = select(Document).where(Document.doc_id.in_(doc_ids))
        docs = list((await self._db.execute(stmt)).scalars())
        doc_map = {d.doc_id: d for d in docs}

        # 5. LLM 답변 생성
        context = "\n\n".join(f"[문서 {i+1}]\n{text}" for i, text in enumerate(chunk_texts))
        prompt = f"""다음 컨텍스트를 기반으로 질문에 답하세요.

컨텍스트:
{context}

질문: {question}

답변 (출처 표시 포함):"""

        provider, used_model = await self._router.select_model(
            task_type="answer",
            required_capabilities=["answer"],
            estimated_tokens=len(context.split()) + 500,
        )

        response = await provider.complete(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.1,
        )

        # 6. 출처 목록 구성
        sources = []
        for r in search_results:
            doc = doc_map.get(r.payload.get("doc_id", ""))
            if doc:
                sources.append({
                    "doc_id": doc.doc_id,
                    "url": doc.url,
                    "title": doc.title,
                    "collected_at": doc.collected_at.isoformat() if doc.collected_at else "",
                    "relevance_score": r.score,
                })

        return {
            "answer": response.content,
            "sources": sources,
            "model_used": used_model.model_name,
            "query": question,
        }
