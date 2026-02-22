"""Thread-safe context store for running Attractor pipelines."""

from __future__ import annotations

from threading import RLock
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping


class Context:
    """Shared key-value state that handlers read and write during execution."""

    def __init__(self, initial: Mapping[str, Any] | None = None) -> None:
        self._values: MutableMapping[str, Any] = dict(initial or {})
        self._lock = RLock()
        self._logs: List[str] = []

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._values[key] = value

    def get(self, key: str, default: Any | None = None) -> Any:
        with self._lock:
            return self._values.get(key, default)

    def update(self, entries: Mapping[str, Any]) -> None:
        with self._lock:
            self._values.update(entries)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._values)

    def append_log(self, entry: str) -> None:
        with self._lock:
            self._logs.append(entry)

    def logs(self) -> List[str]:
        with self._lock:
            return list(self._logs)

    def clone(self) -> "Context":
        with self._lock:
            cloned = Context(self._values)
            cloned._logs = list(self._logs)
            return cloned


def context_from_pairs(pairs: Iterable[str]) -> Context:
    """Build a context from command-line key=value pairs."""

    def parse_entry(pair: str) -> tuple[str, str]:
        if "=" not in pair:
            raise ValueError(f"Invalid context entry '{pair}', expected key=value")
        key, value = pair.split("=", 1)
        return key.strip(), value.strip()

    ctx = Context()
    for pair in pairs:
        key, value = parse_entry(pair)
        ctx.set(key, value)
    return ctx
