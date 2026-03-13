"""Summary Service — 문서 AI 요약 및 관련 문서 검색."""

import asyncio
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import Document
from app.providers.extractor.chain import ExtractionPipeline
from app.services.fetch_service import FetchService
from app.services.model_router import ModelRouter

logger = get_logger(__name__)

_SYSTEM_PROMPT = "당신은 문서 분석 전문가입니다. 주어진 문서를 분석하여 지정된 형식의 한국어 Markdown 요약을 작성합니다."

_SUMMARY_TEMPLATE = """다음 문서를 분석하여 아래 섹션을 모두 포함한 Markdown 요약을 작성하세요.
각 섹션은 ## 헤딩으로 구분하며, 내용이 없는 섹션도 간략히 표기하세요.

## 핵심 요약
(2~3문장의 핵심 내용)

## 배경
(이 주제가 다뤄지는 맥락과 배경)

## 대상 독자
(이 문서가 주로 도움이 되는 독자층)

## 의미/영향
(이 문서의 중요성, 시사점, 실질적 영향)

## 섹션별 요약
(문서의 주요 섹션/단락별 핵심 정리)

## 실무 적용 방안
(실제 업무나 프로젝트에 활용할 수 있는 구체적 방법)

## 키워드
(핵심 키워드를 인라인 코드 형식으로 나열: `키워드1` `키워드2` ...)

---

[문서 제목]: {title}
[문서 본문]:
{text}
"""


class SummaryService:
    """문서 AI 요약 서비스.

    URL을 재수집 → 본문 추출 → LLM 구조화 요약 → Qdrant 관련 문서 검색 → DB 저장.
    """

    def __init__(self, db: AsyncSession, router: ModelRouter) -> None:
        self._db = db
        self._router = router
        self._embedding_model = None
        self._qdrant = None

    def _get_embedding_model(self):
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(settings.embedding_model)
        return self._embedding_model

    def _get_qdrant(self):
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                prefer_grpc=False,
            )
        return self._qdrant

    async def generate(self, doc: Document) -> dict:
        """문서 요약을 생성하고 DB에 저장합니다.

        Returns:
            {"summary": str, "related_docs": list[dict]}
        """
        # 1. URL 재수집
        logger.info("요약 시작: URL 수집", doc_id=doc.doc_id, url=doc.url[:80])
        fetcher = FetchService()
        html_bytes, status_code, _ = await fetcher.fetch_url(doc.url)
        if status_code >= 400:
            raise RuntimeError(f"URL 수집 실패 (HTTP {status_code}): {doc.url}")
        html = html_bytes.decode("utf-8", errors="replace")

        # 2. 본문 추출
        logger.info("본문 추출 중", doc_id=doc.doc_id)
        pipeline = ExtractionPipeline()
        extract_result = await pipeline.extract(html, doc.url)
        text = extract_result.text[:8000]  # 토큰 초과 방지
        title = extract_result.title or doc.title or "(제목 없음)"

        # 3. LLM 구조화 요약 생성
        logger.info("LLM 요약 생성 중", doc_id=doc.doc_id)
        prompt = _SUMMARY_TEMPLATE.format(title=title, text=text)
        provider, model = await self._router.select_model(
            task_type="summary_gen",
            required_capabilities=["answer"],
            estimated_tokens=len(text.split()) + 1500,
        )
        response = await provider.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            response_format="text",
            max_tokens=3000,
            temperature=0.3,
        )
        await self._router.record_usage(model, "summary_gen", response.input_tokens, response.output_tokens)
        summary_md = response.content.strip()

        # 4. Qdrant 관련 문서 검색
        logger.info("관련 문서 검색 중", doc_id=doc.doc_id)
        related_docs = await self._find_related(doc, text)

        # 5. 관련 문서 섹션을 Markdown에 추가
        if related_docs:
            related_section = self._build_related_section(related_docs)
            summary_md = summary_md + "\n\n" + related_section

        # 6. DB 저장
        doc.summary = summary_md
        self._db.add(doc)
        await self._db.commit()
        logger.info("요약 저장 완료", doc_id=doc.doc_id)

        return {"summary": summary_md, "related_docs": related_docs}

    async def _find_related(self, doc: Document, text: str) -> list[dict]:
        """Qdrant 벡터 검색으로 관련 문서 TOP5를 반환합니다."""
        try:
            query_text = f"{doc.title or ''} {text[:300]}".strip()
            loop = asyncio.get_event_loop()
            embedding_model = self._get_embedding_model()
            query_vector = (await loop.run_in_executor(
                None, lambda: embedding_model.encode([query_text]).tolist()
            ))[0]

            qdrant = self._get_qdrant()
            search_results = qdrant.search(
                collection_name=settings.qdrant_collection,
                query_vector=query_vector,
                limit=30,
                with_payload=True,
            )

            # 현재 문서 제외, doc_id별 최고 점수 dedupe
            best_per_doc: dict[str, float] = {}
            for r in search_results:
                result_doc_id = r.payload.get("doc_id", "")
                if result_doc_id == doc.doc_id:
                    continue
                if result_doc_id not in best_per_doc or r.score > best_per_doc[result_doc_id]:
                    best_per_doc[result_doc_id] = r.score

            # 점수 상위 5개
            top5_ids = sorted(best_per_doc, key=lambda k: best_per_doc[k], reverse=True)[:5]
            if not top5_ids:
                return []

            stmt = select(Document).where(Document.doc_id.in_(top5_ids))
            docs = list((await self._db.execute(stmt)).scalars())
            doc_map = {d.doc_id: d for d in docs}

            related = []
            for doc_id in top5_ids:
                d = doc_map.get(doc_id)
                if d:
                    related.append({
                        "doc_id": d.doc_id,
                        "url": d.url,
                        "title": d.title,
                        "relevance_score": round(best_per_doc[doc_id], 4),
                    })
            return related

        except Exception as e:
            logger.warning("관련 문서 검색 실패, 생략", error=str(e))
            return []

    def _build_related_section(self, related_docs: list[dict]) -> str:
        """관련 문서 Markdown 테이블 섹션을 생성합니다."""
        lines = ["## 관련 문서", "", "| 제목 | 유사도 |", "|------|--------|"]
        for d in related_docs:
            title = d.get("title") or d["url"]
            doc_link = f"/documents/{d['doc_id']}"
            score = d["relevance_score"]
            lines.append(f"| [{title}]({doc_link}) | {score:.2f} |")
        return "\n".join(lines)
