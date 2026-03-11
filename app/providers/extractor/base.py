"""Extractor Provider 기반 인터페이스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExtractResult:
    """본문 추출 결과."""
    text: str
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    language: Optional[str] = None
    extractor_used: Optional[str] = None


class BaseExtractor(ABC):
    """본문 추출기 추상 기반 클래스."""

    @abstractmethod
    async def extract(self, html: str, url: str) -> ExtractResult:
        """HTML에서 본문 텍스트를 추출합니다.

        Args:
            html: 원문 HTML 문자열
            url: 원본 URL (추출 힌트용)

        Returns:
            ExtractResult 객체

        Raises:
            ExtractionError: 추출 실패 시
        """
        ...


class ExtractionError(Exception):
    """모든 추출기가 실패했을 때."""
    pass
