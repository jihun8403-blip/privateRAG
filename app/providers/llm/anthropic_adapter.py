"""Anthropic Claude LLM 어댑터."""

import time
from typing import Literal, Optional

import anthropic

from app.core.logging import get_logger
from app.providers.llm.base import BaseLLMProvider, LLMResponse

logger = get_logger(__name__)

_JSON_SYSTEM_SUFFIX = "\n\nRespond only with valid JSON. Do not include any explanation or text outside the JSON."


class AnthropicAdapter(BaseLLMProvider):
    """Anthropic Claude API 어댑터.

    Anthropic은 JSON 모드를 미지원하므로
    response_format='json' 시 system 프롬프트에 JSON 출력 지시를 추가합니다.
    """

    def __init__(self, api_key: str, model_name: str = "claude-haiku-4-5-20251001"):
        self._model_name = model_name
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Literal["text", "json"] = "text",
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        effective_system = system or ""
        if response_format == "json":
            effective_system += _JSON_SYSTEM_SUFFIX

        kwargs: dict = {
            "model": self._model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if effective_system:
            kwargs["system"] = effective_system.strip()

        start = time.monotonic()
        response = await self._client.messages.create(**kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)

        content = response.content[0].text if response.content else ""
        usage = response.usage

        return LLMResponse(
            content=content,
            model_name=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            duration_ms=duration_ms,
        )

    async def health_check(self) -> bool:
        try:
            # 최소 토큰으로 헬스체크
            resp = await self._client.messages.create(
                model=self._model_name,
                max_tokens=5,
                messages=[{"role": "user", "content": "hi"}],
            )
            return resp is not None
        except Exception:
            return False
