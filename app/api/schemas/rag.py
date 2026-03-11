"""RAG 질의응답 Pydantic v2 스키마."""

from typing import Optional

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    topic_ids: Optional[list[str]] = None
    top_k: int = Field(default=5, ge=1, le=20)
    model_id: Optional[str] = None  # FR-A03: 사용자 모델 선택


class RagSource(BaseModel):
    doc_id: str
    url: str
    title: Optional[str] = None
    collected_at: str
    relevance_score: float


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagSource]
    model_used: str
    query: str


class ChunkSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    topic_ids: Optional[list[str]] = None
    top_k: int = Field(default=10, ge=1, le=50)


class ChunkRead(BaseModel):
    chunk_id: str
    doc_id: str
    chunk_index: int
    chunk_text: str
    token_count: Optional[int] = None
    score: Optional[float] = None
