"""Query Planner — LLM 기반 검색 쿼리 생성기."""

import json
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.topic import SearchQuery, Topic
from app.providers.llm.base import BaseLLMProvider
from app.services.model_router import ModelRouter

logger = get_logger(__name__)

SYSTEM_PROMPT = """당신은 웹 검색 전문가입니다.
주어진 토픽 프로파일을 분석하여 효과적인 검색 쿼리를 생성하세요.
반드시 유효한 JSON만 응답하세요."""

QUERY_EXPIRY_DAYS = 7


class QueryItem(BaseModel):
    query: str
    intent: str  # broad | narrow | preferred_domain
    language: str  # ko | en


class QueryPlanResult(BaseModel):
    queries: list[QueryItem]


class QueryPlanner:
    """주제 프로파일 기반 검색 쿼리 자동 생성 (FR-Q01~Q05)."""

    def __init__(self, db: AsyncSession, router: ModelRouter):
        self._db = db
        self._router = router

    async def generate_queries(
        self,
        topic: Topic,
        count_per_lang: int = 3,
    ) -> list[SearchQuery]:
        """주제에 맞는 검색 쿼리를 생성하고 DB에 저장합니다.

        Returns:
            생성된 SearchQuery ORM 객체 목록
        """
        provider, model = await self._router.select_model(
            task_type="query_gen",
            required_capabilities=["query_gen"],
            estimated_tokens=800,
        )

        prompt = self._build_prompt(topic, count_per_lang)

        # 비JSON 응답 시 1회 재시도 (TC-Q04, NFR-05)
        result = await self._call_with_retry(provider, prompt)

        queries_data = result.queries
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=QUERY_EXPIRY_DAYS)

        saved: list[SearchQuery] = []
        for item in queries_data:
            sq = SearchQuery(
                topic_id=topic.topic_id,
                query_text=item.query,
                query_language=item.language,
                intent=item.intent,
                generated_by_model=model.model_name,
                created_at=now,
                expires_at=expires,
            )
            self._db.add(sq)
            saved.append(sq)

        logger.info("쿼리 생성 완료", topic=topic.name, count=len(saved))
        return saved

    def _build_prompt(self, topic: Topic, count_per_lang: int) -> str:
        languages = topic.language.split(",")
        preferred_domains = [
            r.pattern for r in topic.rules
            if r.rule_type == "preferred_domain" and r.enabled
        ]

        domain_hint = ""
        if preferred_domains:
            domain_hint = f"\n선호 도메인: {', '.join(preferred_domains[:3])}\n→ 'site:도메인' 형식의 쿼리도 포함하세요 (intent: preferred_domain)."

        return f"""다음 토픽에 대한 웹 검색 쿼리를 생성하세요.

토픽명: {topic.name}
설명: {topic.description}
필수 포함 키워드: {', '.join(topic.must_include) or '없음'}
제외 키워드: {', '.join(topic.must_exclude) or '없음'}
대상 언어: {', '.join(languages)}{domain_hint}

각 언어별로 {count_per_lang}개씩, intent는 broad/narrow/preferred_domain 중 하나를 사용하세요.

응답 형식 (JSON):
{{
  "queries": [
    {{"query": "검색어", "intent": "broad", "language": "ko"}},
    {{"query": "search term", "intent": "narrow", "language": "en"}}
  ]
}}"""

    async def _call_with_retry(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        max_retries: int = 2,
    ) -> QueryPlanResult:
        last_error: Exception = ValueError("LLM 호출 미시도")
        for attempt in range(max_retries):
            try:
                response = await provider.complete(
                    prompt=prompt,
                    system=SYSTEM_PROMPT,
                    response_format="json",
                    max_tokens=1024,
                    temperature=0.3,
                )
                data = json.loads(response.content)
                return QueryPlanResult.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.warning("쿼리 생성 파싱 실패, 재시도", attempt=attempt + 1, error=str(e))

        raise ValueError(f"쿼리 생성 실패 (최대 재시도 초과): {last_error}") from last_error
