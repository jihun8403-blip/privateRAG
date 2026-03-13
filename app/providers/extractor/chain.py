"""Extractor 3단계 fallback 체인."""

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.extractor.base import BaseExtractor, ExtractResult, ExtractionError
from app.providers.extractor.playwright_extractor import PlaywrightExtractor
from app.providers.extractor.readability_extractor import ReadabilityExtractor
from app.providers.extractor.trafilatura_extractor import TrafilaturaExtractor

logger = get_logger(__name__)


class ExtractionPipeline:
    """trafilatura → readability → playwright 순서의 fallback 체인.

    각 추출기가 실패하거나 최소 길이 미달 시 다음 추출기를 시도합니다.
    """

    def __init__(self) -> None:
        self._extractors: list[BaseExtractor] = [
            TrafilaturaExtractor(),
            ReadabilityExtractor(),
            PlaywrightExtractor(),
        ]
        self._min_length = settings.relevance_min_text_length

    async def extract(self, html: str, url: str) -> ExtractResult:
        """HTML에서 본문을 추출합니다. 모든 추출기 실패 시 ExtractionError 발생."""
        last_error: Exception = ExtractionError("추출기 없음")
        errors: list[str] = []

        for extractor in self._extractors:
            name = extractor.__class__.__name__
            try:
                result = await extractor.extract(html, url)
                if result.text and len(result.text) >= self._min_length:
                    logger.debug(
                        "본문 추출 성공",
                        extractor=name,
                        url=url[:80],
                        length=len(result.text),
                    )
                    return result
                reason = f"본문 너무 짧음 ({len(result.text) if result.text else 0}자)"
                errors.append(f"{name}: {reason}")
                logger.debug("본문 너무 짧음, 다음 추출기 시도", extractor=name, length=len(result.text) if result.text else 0)
            except ExtractionError as e:
                last_error = e
                errors.append(f"{name}: {e}")
                logger.debug("추출기 실패, 다음 시도", extractor=name, error=str(e))
            except Exception as e:
                last_error = e
                errors.append(f"{name}: {e}")
                logger.warning("추출기 예외", extractor=name, error=str(e))

        raise ExtractionError(f"모든 추출기 실패 ({url}): {' | '.join(errors)}") from last_error
