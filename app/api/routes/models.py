"""Models API 라우터 (SDS §6.5)."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbDep
from app.api.schemas.model_registry import (
    ModelRegistryCreate,
    ModelRegistryRead,
    ModelRegistryUpdate,
    ModelUsageLogRead,
    UsageSummary,
)
from app.models.model_registry import ModelRegistry, ModelUsageLog
from app.services.usage_service import UsageService

router = APIRouter()


def _try_register_provider(model: ModelRegistry) -> None:
    """모델을 app_state에 즉시 등록합니다. Ollama는 api_key 불필요, 클라우드는 api_key 필요."""
    from app.core.app_state import register_provider
    key = f"{model.provider}:{model.model_name}"
    try:
        if model.provider == "ollama":
            from app.providers.llm.ollama_adapter import OllamaAdapter
            from app.core.config import settings
            register_provider(key, OllamaAdapter(
                base_url=settings.ollama_base_url,
                model_name=model.model_name,
            ))
        elif model.provider == "openai" and model.api_key:
            from app.providers.llm.openai_adapter import OpenAIAdapter
            register_provider(key, OpenAIAdapter(api_key=model.api_key, model_name=model.model_name))
        elif model.provider == "anthropic" and model.api_key:
            from app.providers.llm.anthropic_adapter import AnthropicAdapter
            register_provider(key, AnthropicAdapter(api_key=model.api_key, model_name=model.model_name))
        elif model.provider in ("google", "gemini"):
            from app.core.config import settings as _s
            api_key = model.api_key or _s.gemini_api_key
            if api_key:
                from app.providers.llm.google_adapter import GoogleAdapter
                register_provider(key, GoogleAdapter(api_key=api_key, model_name=model.model_name))
    except Exception:
        pass  # 어댑터 패키지 미설치 시 무시


@router.get("", response_model=list[ModelRegistryRead])
async def list_models(db: DbDep):
    """모델 목록 조회."""
    stmt = select(ModelRegistry).order_by(ModelRegistry.priority)
    result = await db.execute(stmt)
    return list(result.scalars())


@router.post("", response_model=ModelRegistryRead, status_code=201)
async def create_model(data: ModelRegistryCreate, db: DbDep):
    """모델 등록."""
    model = ModelRegistry(
        provider=data.provider,
        model_name=data.model_name,
        capability_tags=data.capability_tags,
        max_context=data.max_context,
        cost_input_per_1k=data.cost_input_per_1k,
        cost_output_per_1k=data.cost_output_per_1k,
        daily_budget_tokens=data.daily_budget_tokens,
        priority=data.priority,
        fallback_order=data.fallback_order,
        enabled=data.enabled,
        api_key=data.api_key,
    )
    db.add(model)
    await db.flush()
    _try_register_provider(model)
    return model


@router.put("/{model_id}", response_model=ModelRegistryRead)
async def update_model(model_id: str, data: ModelRegistryUpdate, db: DbDep):
    """모델 수정."""
    model = await db.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(model, field, value)
    db.add(model)
    _try_register_provider(model)
    return model


@router.get("/{model_id}/usage", response_model=UsageSummary)
async def get_model_usage(model_id: str, db: DbDep):
    """모델 사용량 조회."""
    svc = UsageService(db)
    try:
        return await svc.get_usage_summary(model_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{model_id}/usage/logs", response_model=list[ModelUsageLogRead])
async def list_usage_logs(model_id: str, db: DbDep, limit: int = 50):
    """모델 사용 로그 조회."""
    model = await db.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다.")

    stmt = (
        select(ModelUsageLog)
        .where(ModelUsageLog.model_id == model_id)
        .order_by(ModelUsageLog.executed_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars())


@router.post("/reset-usage", status_code=200)
async def reset_usage(db: DbDep):
    """토큰 사용량 수동 초기화 (FR-M04)."""
    svc = UsageService(db)
    count = await svc.reset_daily_usage()
    return {"message": f"{count}개 모델의 토큰 사용량이 초기화되었습니다."}
