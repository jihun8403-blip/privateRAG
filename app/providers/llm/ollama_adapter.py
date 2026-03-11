"""Ollama LLM 어댑터 (OpenAI 호환 /api/chat 사용)."""

import time
from typing import Literal, Optional

import httpx

from app.core.logging import get_logger
from app.providers.llm.base import BaseLLMProvider, LLMResponse

logger = get_logger(__name__)


class OllamaAdapter(BaseLLMProvider):
    """Ollama 로컬 LLM 어댑터.

    httpx.AsyncClient를 직접 사용해 /api/chat 엔드포인트를 호출합니다.
    """

    def __init__(self, base_url: str, model_name: str, timeout: int = 120):
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
        )

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

        payload: dict = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if response_format == "json":
            payload["format"] = "json"

        start = time.monotonic()
        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("Ollama API 오류", status=e.response.status_code, model=self._model_name)
            raise
        except httpx.RequestError as e:
            logger.error("Ollama 연결 오류", error=str(e), model=self._model_name)
            raise

        duration_ms = int((time.monotonic() - start) * 1000)
        data = response.json()

        return LLMResponse(
            content=data["message"]["content"],
            model_name=data.get("model", self._model_name),
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            duration_ms=duration_ms,
        )

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
