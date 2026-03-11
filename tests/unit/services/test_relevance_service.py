"""Relevance Service 단위 테스트 (TC-V01~V05)."""

import pytest

from app.services.relevance_service import RelevanceService


class TestRuleFilter:
    def setup_method(self):
        self.svc = RelevanceService(router=None)  # router는 rule_filter에 불필요

    def test_must_include_missing_returns_false(self, sample_topic):
        """TC-V01: must_include 키워드 없으면 False 반환."""
        text = "This is an article about deep learning and neural networks."
        passed, reason = self.svc.rule_filter(text, sample_topic)
        assert not passed
        assert "필수 키워드" in reason

    def test_must_exclude_present_returns_false(self, sample_topic):
        """TC-V02: must_exclude 키워드 포함 시 False 반환."""
        text = "This local llm agent uses openai exclusive API for processing."
        passed, reason = self.svc.rule_filter(text, sample_topic)
        assert not passed
        assert "제외 키워드" in reason

    def test_text_too_short_returns_false(self, sample_topic):
        """TC-V05: 최소 길이 미달 시 False 반환."""
        text = "local llm agent"  # 15자
        passed, reason = self.svc.rule_filter(text, sample_topic)
        assert not passed
        assert "짧음" in reason

    def test_valid_text_passes(self, sample_topic):
        """1차 필터 통과 케이스."""
        text = "local llm agent " * 20  # 충분히 긴 텍스트
        passed, reason = self.svc.rule_filter(text, sample_topic)
        assert passed
        assert reason == ""

    def test_no_must_include_passes_with_length(self):
        """must_include가 없으면 길이만 검사."""
        from app.models.topic import Topic
        topic = Topic(
            topic_id="t-empty",
            name="test",
            description="test",
            must_include=[],
            must_exclude=[],
            relevance_threshold=0.6,
        )
        text = "a" * 300
        passed, _ = RelevanceService(router=None).rule_filter(text, topic)
        assert passed


class TestLlmCheck:
    async def test_score_above_threshold_is_relevant(
        self, sample_topic, mock_relevance_provider, mocker
    ):
        """TC-V03: score >= threshold → is_relevant=True."""
        mock_router = mocker.AsyncMock()
        mock_router.select_model.return_value = (mock_relevance_provider, mocker.MagicMock(model_name="mock"))

        svc = RelevanceService(router=mock_router)
        text = "local llm agent " * 30
        result = await svc.llm_check(text, sample_topic)

        assert result.is_relevant is True
        assert result.score == pytest.approx(0.87)

    async def test_score_below_threshold_is_not_relevant(
        self, sample_topic, mock_low_relevance_provider, mocker
    ):
        """TC-V04: score < threshold → is_relevant=False."""
        mock_router = mocker.AsyncMock()
        mock_router.select_model.return_value = (mock_low_relevance_provider, mocker.MagicMock(model_name="mock"))

        svc = RelevanceService(router=mock_router)
        text = "local llm agent " * 30
        result = await svc.llm_check(text, sample_topic)

        assert result.is_relevant is False
        assert result.score == pytest.approx(0.3)
