"""LLM Provider 기반 인터페이스 및 공통 데이터 클래스."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class LLMResponse:
    """LLM 응답 공통 구조."""
    content: str
    model_name: str
    input_tokens: int
    output_tokens: int
    duration_ms: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class BaseLLMProvider(ABC):
    """모든 LLM 어댑터의 추상 기반 클래스."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Literal["text", "json"] = "text",
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        """텍스트 완성 요청.

        Args:
            prompt: 사용자 입력 프롬프트
            system: 시스템 프롬프트 (선택)
            response_format: "json"이면 JSON 모드 활성화 요청
            max_tokens: 최대 출력 토큰 수
            temperature: 창의성 온도 (0.0~1.0)

        Returns:
            LLMResponse 객체
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """제공자 연결 상태를 확인합니다."""
        ...
