"""Search Provider 기반 인터페이스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SearchResult:
    """검색 결과 단일 항목."""
    url: str
    title: str
    snippet: str
    rank: int
    published_at: Optional[datetime] = None
    extra: dict = field(default_factory=dict)


class BaseSearchProvider(ABC):
    """검색 API 제공자 추상 기반 클래스."""

    @abstractmethod
    async def search(
        self,
        query: str,
        count: int = 10,
        language: str = "ko",
    ) -> list[SearchResult]:
        """쿼리를 실행하고 검색 결과 목록을 반환합니다.

        Args:
            query: 검색 질의문
            count: 반환할 결과 수 (최대값은 제공자마다 다름)
            language: 검색 언어 코드 (ISO 639-1)

        Returns:
            SearchResult 목록 (rank 오름차순)
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """API 연결 상태를 확인합니다."""
        ...
