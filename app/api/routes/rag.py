"""RAG API 라우터 (SDS §6.4)."""

from fastapi import APIRouter, HTTPException

from app.api.deps import DbDep
from app.api.schemas.rag import ChunkRead, ChunkSearchRequest, RagQueryRequest, RagQueryResponse, RagSource
from app.core.app_state import get_providers
from app.services.model_router import ModelRouter
from app.services.rag_service import RagService

router = APIRouter()


def _get_rag_service(db) -> RagService:
    providers = get_providers()
    router_svc = ModelRouter(db, providers)
    return RagService(db, router_svc)


@router.post("/query", response_model=RagQueryResponse)
async def rag_query(request: RagQueryRequest, db: DbDep):
    """자연어 질의응답 (TC-I03, FR-A01~A03)."""
    svc = _get_rag_service(db)
    try:
        result = await svc.query(
            question=request.query,
            topic_ids=request.topic_ids,
            top_k=request.top_k,
            model_id=request.model_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 질의 실패: {e}")

    sources = [
        RagSource(
            doc_id=s["doc_id"],
            url=s["url"],
            title=s.get("title"),
            collected_at=s.get("collected_at", ""),
            relevance_score=s.get("relevance_score", 0.0),
        )
        for s in result["sources"]
    ]

    return RagQueryResponse(
        answer=result["answer"],
        sources=sources,
        model_used=result["model_used"],
        query=result["query"],
    )


@router.get("/chunks", response_model=list[ChunkRead])
async def search_chunks(
    query: str,
    db: DbDep,
    top_k: int = 10,
):
    """청크 유사도 검색."""
    svc = _get_rag_service(db)
    try:
        result = await svc.query(question=query, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"청크 검색 실패: {e}")

    return [
        ChunkRead(
            chunk_id=s.get("doc_id", ""),
            doc_id=s.get("doc_id", ""),
            chunk_index=0,
            chunk_text="",
            score=s.get("relevance_score"),
        )
        for s in result["sources"]
    ]
