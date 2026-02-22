"""Provider adapters for the unified LLM client."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from attractor.unified_llm.models import (
    Message,
    Request,
    Response,
    Role,
    StreamEvent,
    Usage,
)


class ProviderAdapter(ABC):
    """Contract every provider must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def complete(self, request: Request) -> Response:
        raise NotImplementedError

    @abstractmethod
    def stream(self, request: Request) -> Iterator[StreamEvent]:
        raise NotImplementedError


class StubProviderAdapter(ProviderAdapter):
    """Deterministic stub backend for offline runs."""

    @property
    def name(self) -> str:
        return "stub"

    def _build_content(self, request: Request) -> str:
        prompt = ""
        if request.messages:
            prompt = request.messages[-1].content
        goal = prompt.strip()
        return f"Stub provider response for prompt: {goal}"

    def complete(self, request: Request) -> Response:
        content = self._build_content(request)
        return Response(
            content=content,
            usage=Usage(total_tokens=len(content)),
        )

    def stream(self, request: Request) -> Iterator[StreamEvent]:
        content = self._build_content(request)
        yield StreamEvent(content=content, role=Role.ASSISTANT)
