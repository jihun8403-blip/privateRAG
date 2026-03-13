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

SYSTEM_PROMPT = """
당신은 웹 검색 전문가입니다.
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

        logger.info(
            "쿼리 생성 provider 선택",
            provider=f"{model.provider}:{model.model_name}",
            topic=topic.name,
        )

        prompt = self._build_prompt(topic, count_per_lang)

        # 비JSON 응답 시 1회 재시도 (TC-Q04, NFR-05)
        result, input_tokens, output_tokens = await self._call_with_retry(provider, prompt, model_key=f"{model.provider}:{model.model_name}")
        await self._router.record_usage(model, "query_gen", input_tokens, output_tokens)

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
        model_key: str = "",
    ) -> tuple[QueryPlanResult, int, int]:
        last_error: Exception = ValueError("LLM 호출 미시도")
        response = None
        for attempt in range(max_retries):
            # 첫 시도: json 모드, 재시도: text 모드 (빈 응답 대응)
            fmt = "json" if attempt == 0 else "text"
            params = dict(
                response_format=fmt,
                max_tokens=65536,
                temperature=0.3,
            )
            logger.info(
                "LLM 호출",
                model=model_key,
                attempt=attempt + 1,
                prompt_preview=prompt[:300],
                **params,
            )
            try:
                response = await provider.complete(
                    prompt=prompt,
                    system=SYSTEM_PROMPT,
                    **params,
                )
                logger.info(
                    "LLM 응답 수신",
                    model=model_key,
                    attempt=attempt + 1,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    duration_ms=response.duration_ms,
                    raw=response.content[:300],
                )
                content = response.content.strip()
                if not content:
                    raise json.JSONDecodeError("빈 응답", "", 0)
                # text 모드일 경우 ```json ... ``` 코드블록 추출
                if fmt == "text" and "```" in content:
                    import re
                    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
                    if m:
                        content = m.group(1)
                data = json.loads(content)
                return QueryPlanResult.model_validate(data), response.input_tokens, response.output_tokens
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                raw = (response.content[:300] if response else "응답 없음")
                logger.warning(
                    "쿼리 생성 파싱 실패, 재시도",
                    model=model_key,
                    attempt=attempt + 1,
                    error=str(e),
                    raw=raw,
                )

        raise ValueError(f"쿼리 생성 실패 (최대 재시도 초과): {last_error}") from last_error
