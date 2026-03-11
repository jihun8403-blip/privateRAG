"""애플리케이션 전역 상태 (Provider 레지스트리)."""

from app.providers.llm.base import BaseLLMProvider
from app.providers.search.base import BaseSearchProvider

_providers: dict[str, BaseLLMProvider] = {}
_search_provider: BaseSearchProvider | None = None


def register_provider(key: str, provider: BaseLLMProvider) -> None:
    """LLM Provider를 등록합니다. key: 'provider:model_name' 형식."""
    _providers[key] = provider


def get_providers() -> dict[str, BaseLLMProvider]:
    return _providers


def set_search_provider(provider: BaseSearchProvider) -> None:
    global _search_provider
    _search_provider = provider


def get_search_provider() -> BaseSearchProvider:
    if _search_provider is None:
        raise RuntimeError("Search provider가 초기화되지 않았습니다.")
    return _search_provider
