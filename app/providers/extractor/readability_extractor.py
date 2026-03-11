"""readability-lxml 기반 본문 추출기 (2순위 fallback)."""

import asyncio

from app.core.logging import get_logger
from app.providers.extractor.base import BaseExtractor, ExtractResult, ExtractionError

logger = get_logger(__name__)


def _sync_extract(html: str, url: str) -> dict:
    """동기 readability 추출 (run_in_executor용)."""
    from readability import Document
    doc = Document(html, url=url)
    content = doc.summary(html_partial=False)
    title = doc.title()

    # HTML 태그 제거 (간단 버전)
    import re
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()
    return {"text": text, "title": title}


class ReadabilityExtractor(BaseExtractor):
    """readability-lxml 기반 본문 추출기.

    trafilatura 실패 시 2순위로 시도됩니다.
    """

    async def extract(self, html: str, url: str) -> ExtractResult:
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, _sync_extract, html, url)
        except Exception as e:
            raise ExtractionError(f"readability: 추출 실패 ({url}): {e}") from e

        if not data.get("text") or len(data["text"]) < 50:
            raise ExtractionError(f"readability: 본문 너무 짧음 ({url})")

        return ExtractResult(
            text=data["text"],
            title=data.get("title"),
            extractor_used="readability",
        )
