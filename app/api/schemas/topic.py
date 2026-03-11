"""Topic 도메인 Pydantic v2 스키마."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TopicRuleBase(BaseModel):
    rule_type: str = Field(..., pattern="^(preferred_domain|blocked_domain|include|exclude)$")
    pattern: str = Field(..., min_length=1)
    is_regex: bool = True
    enabled: bool = True
    priority: int = 0


class TopicRuleCreate(TopicRuleBase):
    pass


class TopicRuleUpdate(BaseModel):
    rule_type: Optional[str] = None
    pattern: Optional[str] = None
    is_regex: Optional[bool] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class TopicRuleRead(TopicRuleBase):
    model_config = ConfigDict(from_attributes=True)
    rule_id: str
    topic_id: str
    created_at: datetime
    updated_at: datetime


class TopicBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    language: str = Field(default="ko,en")
    priority: int = Field(default=5, ge=1, le=10)
    enabled: bool = True
    schedule_cron: str = Field(default="0 */6 * * *")
    relevance_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    must_include: list[str] = Field(default_factory=list)
    must_exclude: list[str] = Field(default_factory=list)

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError("cron 표현식은 5개 필드여야 합니다 (분 시 일 월 요일)")
        return v


class TopicCreate(TopicBase):
    rules: list[TopicRuleCreate] = Field(default_factory=list)


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    language: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    enabled: Optional[bool] = None
    schedule_cron: Optional[str] = None
    relevance_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    must_include: Optional[list[str]] = None
    must_exclude: Optional[list[str]] = None


class TopicRead(TopicBase):
    model_config = ConfigDict(from_attributes=True)
    topic_id: str
    created_at: datetime
    updated_at: datetime
    rules: list[TopicRuleRead] = Field(default_factory=list)


class TopicSummary(BaseModel):
    """목록 조회용 요약 스키마."""
    model_config = ConfigDict(from_attributes=True)
    topic_id: str
    name: str
    description: str
    priority: int
    enabled: bool
    schedule_cron: str
    created_at: datetime
