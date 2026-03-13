"""Search Service — 검색 API 실행 및 URL 수집."""

import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.run_log import SearchRun
from app.models.topic import SearchQuery, Topic
from app.providers.search.base import BaseSearchProvider, SearchResult
from app.services.rule_engine import RuleSet, classify_url

logger = get_logger(__name__)


class SearchService:
    """검색 API 호출 및 URL 필터링·중복 제거 서비스 (FR-R01~R03, FR-R05)."""

    def __init__(self, db: AsyncSession, provider: BaseSearchProvider):
        self._db = db
        self._provider = provider

    async def run_search(
        self,
        topic: Topic,
        queries: list[SearchQuery],
        rule_set: RuleSet,
    ) -> tuple[SearchRun, list[str]]:
        """쿼리 목록으로 검색을 실행하고 필터링된 URL 목록을 반환합니다.

        Returns:
            (SearchRun, 필터링된 URL 목록)
        """
        run = SearchRun(
            topic_id=topic.topic_id,
            query_id=queries[0].query_id if queries else None,
            provider=type(self._provider).__name__,
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        self._db.add(run)

        all_results: list[SearchResult] = []

        for idx, query in enumerate(queries):
            if idx > 0:
                await asyncio.sleep(1.5)  # Brave API rate limit 방지
            try:
                results = await self._provider.search(
                    query=query.query_text,
                    count=10,
                    language=query.query_language,
                )
                all_results.extend(results)
                logger.debug("검색 완료", query=query.query_text[:50], count=len(results))
            except Exception as e:
                logger.warning("검색 실패", query=query.query_text[:50], error=str(e))

        # URL 필터링 및 중복 제거 (FR-R02, FR-R03)
        seen: set[str] = set()
        filtered_urls: list[str] = []

        for result in sorted(all_results, key=lambda r: r.rank):
            url = result.url
            if url in seen:
                continue
            seen.add(url)

            classification, _ = classify_url(url, rule_set)
            if classification == "blocked":
                logger.debug("차단 URL 제외", url=url[:80])
                continue

            filtered_urls.append(url)

        run.status = "success"
        run.result_count = len(filtered_urls)
        run.finished_at = datetime.now(timezone.utc)
        self._db.add(run)

        logger.info(
            "검색 실행 완료",
            topic=topic.name,
            total=len(all_results),
            filtered=len(filtered_urls),
        )
        return run, filtered_urls
