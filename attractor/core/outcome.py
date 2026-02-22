"""Outcome types produced by handler execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class StageStatus(Enum):
    """Canonical statuses returned by handlers."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    RETRY = "retry"
    FAIL = "fail"
    SKIPPED = "skipped"


@dataclass
class Outcome:
    status: StageStatus
    notes: str = ""
    context_updates: Dict[str, Any] = field(default_factory=dict)
    preferred_label: str | None = None
    suggested_next_ids: List[str] = field(default_factory=list)
    failure_reason: str | None = None
