"""Helpers for evaluating edge guard expressions."""

from __future__ import annotations

from typing import Mapping

from attractor.core.context import Context


def evaluate_condition(expression: str | None, context: Context, graph_attrs: Mapping[str, object]) -> bool:
    """Evaluate boolean guard expressions against user-visible state."""

    if not expression:
        return True
    namespace = {
        "context": context.snapshot(),
        "graph": dict(graph_attrs),
    }
    try:
        return bool(eval(expression, {"__builtins__": {}}, namespace))
    except Exception:
        return False
