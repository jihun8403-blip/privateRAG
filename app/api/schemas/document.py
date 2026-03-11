"""Document 도메인 Pydantic v2 스키마."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version_id: str
    doc_id: str
    version_no: int
    content_hash: str
    summary: Optional[str] = None
    relevance_score: Optional[float] = None
    created_at: datetime
    change_type: str


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    doc_id: str
    topic_id: str
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: datetime
    language: Optional[str] = None
    summary: Optional[str] = None
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None
    current_version: int
    is_active: bool
    archive_tier: str
    created_at: datetime
    updated_at: datetime


class DocumentListParams(BaseModel):
    topic_id: Optional[str] = None
    archive_tier: Optional[str] = None
    is_active: Optional[bool] = True
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
