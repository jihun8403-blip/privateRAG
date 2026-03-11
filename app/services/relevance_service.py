"""Relevance Service — 2단계 관련성 검증."""

import json

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.logging import get_logger
from app.models.topic import Topic
from app.providers.llm.base import BaseLLMProvider
from app.services.model_router import ModelRouter

logger = get_logger(__name__)


class RelevanceResult(BaseModel):
    is_relevant: bool
    score: float
    reason: str


class RelevanceService:
    """2단계 관련성 검증 서비스 (FR-V01~V04).

    1단계: 규칙 기반 필터 (키워드/길이)
    2단계: LLM 의미 검증
    """

    def __init__(self, router: ModelRouter):
        self._router = router

    def rule_filter(self, text: str, topic: Topic) -> tuple[bool, str]:
        """1차 규칙 기반 필터 (TC-V01, TC-V02, TC-V05).

        Returns:
            (통과 여부, 실패 이유)
        """
        # 최소 길이 검사
        if len(text) < settings.relevance_min_text_length:
            return False, f"본문 너무 짧음 ({len(text)}자 < {settings.relevance_min_text_length}자)"

        text_lower = text.lower()

        # must_include: 1개 이상 포함해야 함
        if topic.must_include:
            if not any(kw.lower() in text_lower for kw in topic.must_include):
                return False, f"필수 키워드 미포함: {topic.must_include}"

        # must_exclude: 1개라도 있으면 폐기
        if topic.must_exclude:
            for kw in topic.must_exclude:
                if kw.lower() in text_lower:
                    return False, f"제외 키워드 포함: '{kw}'"

        return True, ""

    async def llm_check(
        self,
        text: str,
        topic: Topic,
        title: str = "",
    ) -> RelevanceResult:
        """2차 LLM 의미 검증 (TC-V03, TC-V04).

        Returns:
            RelevanceResult (is_relevant, score, reason)
        """
        provider, model = await self._router.select_model(
            task_type="relevance_check",
            required_capabilities=["relevance_check"],
            estimated_tokens=600,
        )

        prompt = f"""다음 문서가 아래 토픽과 관련이 있는지 판단하세요.

토픽: {topic.name}
토픽 설명: {topic.description}
필수 키워드: {', '.join(topic.must_include) or '없음'}

문서 제목: {title or '(없음)'}
문서 내용 (앞 500자):
{text[:500]}

임계값: {topic.relevance_threshold}

응답 형식 (JSON):
{{"is_relevant": true/false, "score": 0.0~1.0, "reason": "판단 이유"}}"""

        for attempt in range(2):
            try:
                response = await provider.complete(
                    prompt=prompt,
                    response_format="json",
                    max_tokens=256,
                    temperature=0.0,
                )
                data = json.loads(response.content)
                result = RelevanceResult.model_validate(data)
                # threshold 적용
                result.is_relevant = result.score >= topic.relevance_threshold
                logger.debug(
                    "LLM 관련성 검증",
                    score=result.score,
                    relevant=result.is_relevant,
                    topic=topic.name,
                )
                return result
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning("관련성 파싱 실패", attempt=attempt + 1, error=str(e))

        # 파싱 실패 시 안전하게 관련없음 처리
        return RelevanceResult(is_relevant=False, score=0.0, reason="LLM 응답 파싱 실패")
