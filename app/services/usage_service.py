"""Usage Service — 토큰 사용량 기록 및 일일 리셋."""

from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.model_registry import ModelRegistry, ModelUsageLog
from app.providers.llm.base import LLMResponse

logger = get_logger(__name__)


class UsageService:
    """모델 토큰 사용량 관리 서비스."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def log_usage(
        self,
        model_id: str,
        task_type: str,
        response: LLMResponse,
        status: str = "success",
    ) -> ModelUsageLog:
        """LLM 호출 결과를 model_usage_logs에 기록합니다 (TC-M05).

        model_registry.used_tokens_today도 함께 증가시킵니다.
        """
        model = await self._db.get(ModelRegistry, model_id)
        if model is None:
            raise ValueError(f"model_id={model_id} 없음")

        cost = (
            response.input_tokens / 1000 * model.cost_input_per_1k
            + response.output_tokens / 1000 * model.cost_output_per_1k
        )

        log = ModelUsageLog(
            model_id=model_id,
            task_type=task_type,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_estimate=cost,
            executed_at=datetime.now(timezone.utc),
            status=status,
        )
        self._db.add(log)

        # used_tokens_today 누적
        model.used_tokens_today += response.total_tokens
        self._db.add(model)

        return log

    async def reset_daily_usage(self) -> int:
        """모든 모델의 일일 토큰 사용량을 0으로 초기화합니다 (TC-M04, FR-SC02).

        Returns:
            초기화된 모델 수
        """
        today = date.today()
        stmt = (
            update(ModelRegistry)
            .values(used_tokens_today=0, last_reset_date=today)
        )
        result = await self._db.execute(stmt)
        logger.info("일일 토큰 사용량 초기화", date=str(today), rows=result.rowcount)
        return result.rowcount

    async def get_usage_summary(self, model_id: str) -> dict:
        """특정 모델의 사용량 요약을 반환합니다."""
        model = await self._db.get(ModelRegistry, model_id)
        if model is None:
            raise ValueError(f"model_id={model_id} 없음")

        return {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "provider": model.provider,
            "used_tokens_today": model.used_tokens_today,
            "daily_budget_tokens": model.daily_budget_tokens,
            "budget_remaining": max(0, model.daily_budget_tokens - model.used_tokens_today),
            "last_reset_date": model.last_reset_date,
        }
