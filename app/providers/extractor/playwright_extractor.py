"""Playwright 기반 본문 추출기 (3순위 최종 fallback)."""

from app.core.logging import get_logger
from app.providers.extractor.base import BaseExtractor, ExtractResult, ExtractionError
from app.providers.extractor.trafilatura_extractor import TrafilaturaExtractor

logger = get_logger(__name__)


class PlaywrightExtractor(BaseExtractor):
    """Playwright 헤드리스 브라우저 추출기.

    JS 렌더링이 필요한 페이지에 사용합니다.
    렌더링 후 HTML을 trafilatura로 재추출합니다.
    """

    async def extract(self, html: str, url: str) -> ExtractResult:
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise ExtractionError("playwright가 설치되지 않았습니다.") from e

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (compatible; PrivateRAG/1.0)",
                    )
                    page = await context.new_page()
                    await page.goto(url, wait_until="networkidle", timeout=30_000)
                    rendered_html = await page.content()
                finally:
                    await browser.close()
        except Exception as e:
            raise ExtractionError(f"playwright: 페이지 렌더링 실패 ({url}): {e}") from e

        # 렌더링된 HTML을 trafilatura로 재처리
        extractor = TrafilaturaExtractor()
        result = await extractor.extract(rendered_html, url)
        result.extractor_used = "playwright"
        return result
