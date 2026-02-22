"""Simplified coding agent loop that talks to a unified LLM client."""

from __future__ import annotations

from attractor.core.context import Context
from attractor.unified_llm.client import Client
from attractor.unified_llm.models import Message, Request, Role


class CodingAgentLoop:
    def __init__(self, client: Client, provider: str = "stub", model: str = "stub-model") -> None:
        self.client = client
        self.provider = provider
        self.model = model

    def run(self, prompt: str, context: Context) -> str:
        messages = [
            Message(role=Role.SYSTEM, content="You are an autonomous coding agent."),
            Message(role=Role.USER, content=prompt),
        ]
        request = Request(messages=messages, model=self.model, provider=self.provider)
        response = self.client.complete(request)
        return response.content
