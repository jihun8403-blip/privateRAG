"""Model Router — capability/priority/budget 기반 LLM 모델 선택기."""

import asyncio
import time
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.model_registry import ModelRegistry
from app.providers.llm.base import BaseLLMProvider

logger = get_logger(__name__)


class NoAvailableModelError(Exception):
    """사용 가능한 모델이 없을 때 (TC-M03)."""
    pass


class ModelRouter:
    """ModelRegistry 기반 LLM 모델 선택기.

    capability_tags, 일일 토큰 예산, 우선순위 순으로 최적 모델을 선택합니다.
    예산 초과 또는 health_check 실패 시 다음 후보로 fallback합니다.
    """

    # 모델 마지막 호출 시각 (model_id → monotonic timestamp). 앱 전역 공유.
    _last_called: dict[str, float] = {}

    def __init__(
        self,
        db: AsyncSession,
        providers: dict[str, BaseLLMProvider],
    ):
        self._db = db
        self._providers = providers  # key: "provider:model_name"

    async def select_model(
        self,
        task_type: str,
        required_capabilities: list[str],
        estimated_tokens: int = 500,
    ) -> tuple[BaseLLMProvider, ModelRegistry]:
        """task_type에 맞는 최적 모델과 Provider를 반환합니다.

        Args:
            task_type: 작업 유형 (query_gen, relevance_check, answer 등)
            required_capabilities: 필요 capability 태그 목록
            estimated_tokens: 예상 토큰 수 (예산 체크용)

        Returns:
            (BaseLLMProvider, ModelRegistry) 튜플

        Raises:
            NoAvailableModelError: 사용 가능한 모델 없음
        """
        # 활성 모델 전체 로드 (SQLite에서 JSON 배열 containment 미지원 → Python 필터)
        stmt = (
            select(ModelRegistry)
            .where(ModelRegistry.enabled == True)
            .order_by(ModelRegistry.priority, ModelRegistry.fallback_order)
        )
        result = await self._db.execute(stmt)
        all_models: list[ModelRegistry] = list(result.scalars().all())

        # capability 필터
        capable_models = [
            m for m in all_models
            if all(cap in (m.capability_tags or []) for cap in required_capabilities)
        ]

        if not capable_models:
            raise NoAvailableModelError(
                f"capability {required_capabilities}를 지원하는 모델이 없습니다."
            )

        for model in capable_models:
            if not self._can_run(model, estimated_tokens):
                logger.debug("예산 초과 스킵", model=model.model_name, task=task_type)
                continue

            provider_key = f"{model.provider}:{model.model_name}"
            provider = self._providers.get(provider_key)
            if provider is None:
                logger.debug("Provider 미등록 스킵", key=provider_key)
                continue

            if not await provider.health_check():
                logger.warning("Provider health_check 실패", key=provider_key)
                continue

            # 호출 간격 적용
            interval = getattr(model, "call_interval_seconds", 0.0) or 0.0
            if interval > 0:
                last = ModelRouter._last_called.get(model.model_id, 0.0)
                elapsed = time.monotonic() - last
                wait = interval - elapsed
                if wait > 0:
                    logger.info("호출 간격 대기", model=model.model_name, interval_sec=interval, wait_sec=round(wait, 2))
                    await asyncio.sleep(wait)
                else:
                    logger.info("호출 간격 통과", model=model.model_name, interval_sec=interval, elapsed_sec=round(elapsed, 2))

            logger.debug("모델 선택", model=model.model_name, task=task_type)
            return provider, model

        raise NoAvailableModelError(
            f"task_type={task_type}: 예산/health_check 통과 모델 없음"
        )

    def _can_run(self, model: ModelRegistry, estimated_tokens: int) -> bool:
        """일일 예산 내에서 실행 가능한지 확인합니다 (TC-M02)."""
        return (model.used_tokens_today + estimated_tokens) <= model.daily_budget_tokens

    async def record_usage(
        self,
        model: ModelRegistry,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """토큰 사용량을 model_registry에 반영합니다."""
        model.used_tokens_today += input_tokens + output_tokens

        # 오늘 날짜로 last_reset_date 갱신
        today = date.today()
        if model.last_reset_date != today:
            model.used_tokens_today = input_tokens + output_tokens
            model.last_reset_date = today

        self._db.add(model)
        ModelRouter._last_called[model.model_id] = time.monotonic()
