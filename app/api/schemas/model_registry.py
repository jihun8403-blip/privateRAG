"""ModelRegistry 도메인 Pydantic v2 스키마."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelRegistryBase(BaseModel):
    provider: str = Field(..., pattern="^(openai|ollama|anthropic|gemini|google)$")
    model_name: str = Field(..., min_length=1, max_length=100)
    capability_tags: list[str] = Field(default_factory=list)
    max_context: Optional[int] = None
    cost_input_per_1k: float = 0.0
    cost_output_per_1k: float = 0.0
    daily_budget_tokens: int = Field(default=999_999_999, ge=1)
    priority: int = Field(default=10, ge=1)
    fallback_order: int = Field(default=99, ge=1)
    enabled: bool = True
    call_interval_seconds: float = Field(default=0.0, ge=0.0)


class ModelRegistryCreate(ModelRegistryBase):
    api_key: Optional[str] = None


class ModelRegistryUpdate(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    capability_tags: Optional[list[str]] = None
    max_context: Optional[int] = None
    cost_input_per_1k: Optional[float] = None
    cost_output_per_1k: Optional[float] = None
    daily_budget_tokens: Optional[int] = None
    priority: Optional[int] = None
    fallback_order: Optional[int] = None
    enabled: Optional[bool] = None
    api_key: Optional[str] = None
    call_interval_seconds: Optional[float] = None


class ModelRegistryRead(ModelRegistryBase):
    model_config = ConfigDict(from_attributes=True)
    model_id: str
    used_tokens_today: int
    last_reset_date: Optional[date] = None


class ModelUsageLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    usage_id: str
    model_id: str
    task_type: str
    input_tokens: int
    output_tokens: int
    cost_estimate: float
    executed_at: datetime
    status: str


class UsageSummary(BaseModel):
    """모델별 일일 사용량 요약."""
    model_id: str
    model_name: str
    provider: str
    used_tokens_today: int
    daily_budget_tokens: int
    budget_remaining: int
    last_reset_date: Optional[date] = None
