"""Brave Search API 어댑터."""

from datetime import datetime
from typing import Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.providers.search.base import BaseSearchProvider, SearchResult

logger = get_logger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchAdapter(BaseSearchProvider):
    """Brave Search API v1 어댑터.

    tenacity로 3회 재시도 (NFR-05 준수).
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("BRAVE_API_KEY가 설정되지 않았습니다.")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            timeout=httpx.Timeout(30.0),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        count: int = 10,
        language: str = "ko",
    ) -> list[SearchResult]:
        params = {
            "q": query,
            "count": min(count, 20),  # Brave API 최대 20
            "search_lang": language,
            "text_decorations": "false",
            "spellcheck": "false",
        }

        try:
            response = await self._client.get(BRAVE_SEARCH_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning("Brave API 오류", status=e.response.status_code, query=query)
            raise

        data = response.json()
        results = []

        web_results = data.get("web", {}).get("results", [])
        for rank, item in enumerate(web_results, start=1):
            published_at: Optional[datetime] = None
            if age := item.get("page_age"):
                try:
                    published_at = datetime.fromisoformat(age.replace("Z", "+00:00"))
                except ValueError:
                    pass

            results.append(
                SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("description", ""),
                    rank=rank,
                    published_at=published_at,
                )
            )

        logger.info("Brave 검색 완료", query=query[:50], result_count=len(results))
        return results

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(
                BRAVE_SEARCH_URL,
                params={"q": "test", "count": 1},
                timeout=5.0,
            )
            return response.status_code in (200, 422)
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
