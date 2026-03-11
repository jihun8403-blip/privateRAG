"""Fetch Service — URL HTTP 수집 및 원문 저장."""

import asyncio
import hashlib
import time
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; PrivateRAG/1.0; +https://github.com/privaterag)"


class FetchService:
    """URL HTTP 수집 서비스 (FR-R04, NFR-05).

    - 최대 동시 요청: semaphore(5)
    - 도메인별 1초 딜레이 (정중한 크롤링)
    - 최대 3회 재시도
    """

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(settings.search_max_concurrent_fetches)
        self._domain_last_fetch: dict[str, float] = {}

    async def fetch_url(self, url: str) -> tuple[bytes, int, str]:
        """URL을 가져와 (바이트, HTTP 상태코드, 최종 URL) 반환합니다.

        NFR-05: 실패 시 최대 3회 재시도.
        """
        domain = urlparse(url).netloc
        await self._respect_delay(domain)

        async with self._semaphore:
            return await self._fetch_with_retry(url, domain)

    async def _respect_delay(self, domain: str) -> None:
        """도메인별 요청 간격을 유지합니다."""
        last = self._domain_last_fetch.get(domain, 0.0)
        elapsed = time.monotonic() - last
        if elapsed < settings.search_domain_delay_seconds:
            await asyncio.sleep(settings.search_domain_delay_seconds - elapsed)
        self._domain_last_fetch[domain] = time.monotonic()

    async def _fetch_with_retry(
        self, url: str, domain: str, max_retries: int = 3
    ) -> tuple[bytes, int, str]:
        last_error: Exception = httpx.RequestError("초기화 오류")
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(
                    headers={"User-Agent": _USER_AGENT},
                    follow_redirects=True,
                    timeout=httpx.Timeout(30.0),
                ) as client:
                    response = await client.get(url)
                    logger.debug(
                        "URL 수집 성공",
                        url=url[:80],
                        status=response.status_code,
                        attempt=attempt + 1,
                    )
                    return response.content, response.status_code, str(response.url)
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (403, 404, 410):
                    break  # 재시도 무의미한 오류
                logger.warning("HTTP 오류, 재시도", url=url[:80], attempt=attempt + 1, status=e.response.status_code)
            except httpx.RequestError as e:
                last_error = e
                logger.warning("연결 오류, 재시도", url=url[:80], attempt=attempt + 1, error=str(e))

            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 지수 백오프

        raise last_error

    def compute_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
