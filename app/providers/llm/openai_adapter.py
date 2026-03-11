"""OpenAI LLM 어댑터."""

import time
from typing import Literal, Optional

from openai import AsyncOpenAI

from app.core.logging import get_logger
from app.providers.llm.base import BaseLLMProvider, LLMResponse

logger = get_logger(__name__)


class OpenAIAdapter(BaseLLMProvider):
    """OpenAI API 어댑터."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self._model_name = model_name
        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Literal["text", "json"] = "text",
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {
            "model": self._model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        start = time.monotonic()
        response = await self._client.chat.completions.create(**kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)

        content = response.choices[0].message.content or ""
        usage = response.usage

        return LLMResponse(
            content=content,
            model_name=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            duration_ms=duration_ms,
        )

    async def health_check(self) -> bool:
        try:
            models = await self._client.models.list()
            return len(models.data) > 0
        except Exception:
            return False
