"""Usage Service 단위 테스트 (TC-M04~M05)."""

from datetime import date, timedelta

import pytest
from freezegun import freeze_time

from app.providers.llm.base import LLMResponse
from app.services.usage_service import UsageService


class TestUsageService:
    async def test_log_usage_records_tokens(self, db_session, sample_model_a):
        """TC-M05: LLM 호출 후 토큰 사용량 기록."""
        svc = UsageService(db_session)
        response = LLMResponse(
            content="test",
            model_name="qwen2.5:7b",
            input_tokens=200,
            output_tokens=100,
        )

        log = await svc.log_usage(
            model_id=sample_model_a.model_id,
            task_type="query_gen",
            response=response,
        )
        await db_session.flush()

        assert log.input_tokens == 200
        assert log.output_tokens == 100
        assert log.task_type == "query_gen"
        # used_tokens_today 반영
        assert sample_model_a.used_tokens_today == 300

    async def test_reset_daily_usage(self, db_session, sample_model_a):
        """TC-M04: 일일 리셋 후 used_tokens_today=0."""
        sample_model_a.used_tokens_today = 50000
        db_session.add(sample_model_a)
        await db_session.flush()

        svc = UsageService(db_session)
        count = await svc.reset_daily_usage()

        assert count >= 1
        await db_session.refresh(sample_model_a)
        assert sample_model_a.used_tokens_today == 0
        assert sample_model_a.last_reset_date == date.today()

    async def test_get_usage_summary(self, db_session, sample_model_a):
        """모델 사용량 요약 반환."""
        sample_model_a.used_tokens_today = 1000
        db_session.add(sample_model_a)
        await db_session.flush()

        svc = UsageService(db_session)
        summary = await svc.get_usage_summary(sample_model_a.model_id)

        assert summary["used_tokens_today"] == 1000
        assert summary["budget_remaining"] == 10000 - 1000
