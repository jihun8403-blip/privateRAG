"""Model Router 단위 테스트 (TC-M01~M03)."""

import pytest

from app.services.model_router import ModelRouter, NoAvailableModelError


class TestModelRouter:
    async def test_capability_based_selection(
        self, db_session, sample_model_a, sample_model_b, mock_llm_provider
    ):
        """TC-M01: capability 기반 모델 선택."""
        providers = {
            "ollama:qwen2.5:7b": mock_llm_provider,
            "ollama:llama3.2:3b": mock_llm_provider,
        }
        router = ModelRouter(db_session, providers)

        provider, model = await router.select_model(
            task_type="query_gen",
            required_capabilities=["query_gen"],
        )
        # model_a만 query_gen 지원
        assert model.model_id == "m001"

    async def test_budget_exceeded_falls_back(
        self, db_session, sample_model_a, sample_model_b, mock_llm_provider
    ):
        """TC-M02: 예산 초과 시 fallback 모델 선택."""
        # model_a 예산 소진
        sample_model_a.used_tokens_today = 10000
        db_session.add(sample_model_a)
        await db_session.flush()

        providers = {
            "ollama:qwen2.5:7b": mock_llm_provider,
            "ollama:llama3.2:3b": mock_llm_provider,
        }
        router = ModelRouter(db_session, providers)

        provider, model = await router.select_model(
            task_type="relevance_check",
            required_capabilities=["relevance_check"],
            estimated_tokens=100,
        )
        # model_a는 예산 소진, model_b로 fallback
        assert model.model_id == "m002"

    async def test_no_available_model_raises(self, db_session, sample_model_a, mocker):
        """TC-M03: 모든 모델 사용 불가 시 NoAvailableModelError."""
        # model_a 예산 소진
        sample_model_a.used_tokens_today = 10000
        db_session.add(sample_model_a)
        await db_session.flush()

        providers = {"ollama:qwen2.5:7b": mocker.AsyncMock(health_check=mocker.AsyncMock(return_value=False))}
        router = ModelRouter(db_session, providers)

        with pytest.raises(NoAvailableModelError):
            await router.select_model("query_gen", ["query_gen"], estimated_tokens=100)

    def test_can_run_within_budget(self, sample_model_a):
        """예산 내에서 실행 가능 여부 확인."""
        from app.db.session import AsyncSessionLocal
        router = ModelRouter.__new__(ModelRouter)  # __init__ 우회

        sample_model_a.daily_budget_tokens = 1000
        sample_model_a.used_tokens_today = 900

        assert router._can_run(sample_model_a, 100) is True
        assert router._can_run(sample_model_a, 101) is False
