"""Data models shared across the unified LLM client."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Role(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class Usage:
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class Request:
    messages: List[Message]
    model: str
    provider: str | None = None


@dataclass
class Response:
    content: str
    usage: Usage = field(default_factory=Usage)


@dataclass
class StreamEvent:
    content: str
    role: Role
    event_type: str = "message"
