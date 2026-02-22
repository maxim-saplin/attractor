"""Core unified client implementation."""

from __future__ import annotations

from typing import Dict, Iterable, Iterator, Mapping

from attractor.unified_llm.models import Request, Response, StreamEvent
from attractor.unified_llm.providers import ProviderAdapter


class Client:
    """Routes requests to the registered provider adapters."""

    def __init__(
        self,
        providers: Mapping[str, ProviderAdapter],
        default_provider: str | None = None,
    ) -> None:
        self._providers: Dict[str, ProviderAdapter] = dict(providers)
        self._default_provider = default_provider

    def complete(self, request: Request) -> Response:
        adapter = self._resolve(request.provider)
        return adapter.complete(request)

    def stream(self, request: Request) -> Iterator[StreamEvent]:
        adapter = self._resolve(request.provider)
        return adapter.stream(request)

    def _resolve(self, provider: str | None) -> ProviderAdapter:
        provider_name = provider or self._default_provider
        if not provider_name:
            raise ValueError("No provider configured for the request")
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' is not registered")
        return self._providers[provider_name]

    def providers(self) -> Iterable[str]:
        return list(self._providers.keys())
