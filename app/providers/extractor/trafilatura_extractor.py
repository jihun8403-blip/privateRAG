"""trafilatura 기반 본문 추출기 (1순위)."""

import asyncio
from typing import Optional

import trafilatura

from app.core.logging import get_logger
from app.providers.extractor.base import BaseExtractor, ExtractResult, ExtractionError

logger = get_logger(__name__)


def _sync_extract(html: str, url: str) -> Optional[dict]:
    """동기 trafilatura 추출 (run_in_executor용)."""
    result = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        output_format="json",
        with_metadata=True,
    )
    if result:
        import json
        try:
            return json.loads(result)
        except Exception:
            return {"text": result}
    return None


class TrafilaturaExtractor(BaseExtractor):
    """trafilatura 기반 본문 추출기.

    trafilatura는 동기 라이브러리이므로 asyncio.get_event_loop().run_in_executor로 래핑합니다.
    """

    async def extract(self, html: str, url: str) -> ExtractResult:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _sync_extract, html, url)

        if not data or not data.get("text") or len(data.get("text", "")) < 50:
            raise ExtractionError(f"trafilatura: 본문 추출 실패 또는 너무 짧음 ({url})")

        from datetime import datetime
        published_at = None
        if date_str := data.get("date"):
            try:
                published_at = datetime.fromisoformat(date_str)
            except ValueError:
                pass

        return ExtractResult(
            text=data["text"],
            title=data.get("title"),
            author=data.get("author"),
            published_at=published_at,
            language=data.get("language"),
            extractor_used="trafilatura",
        )
