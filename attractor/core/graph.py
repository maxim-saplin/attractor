"""Graph model for Attractor pipelines."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import pydot


@dataclass
class Duration:
    """Describes a duration literal (e.g., 30s, 5m)."""

    value: int
    unit: str

    UNIT_TO_SECONDS = {
        "ms": 0.001,
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86_400,
    }

    def to_seconds(self) -> float:
        return self.value * self.UNIT_TO_SECONDS.get(self.unit, 1)


def _parse_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        raw = raw[1:-1]
    if not raw:
        return ""
    lower = raw.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    duration_match = re.match(r"^(-?\d+)(ms|s|m|h|d)$", raw)
    if duration_match:
        value, unit = duration_match.groups()
        return Duration(int(value), unit)
    if re.match(r"^-?\d+$", raw):
        return int(raw)
    if re.match(r"^-?\d+\.\d+$", raw):
        return float(raw)
    return raw


def _parse_attrs(attrs: Mapping[str, str]) -> Dict[str, Any]:
    return {key: _parse_value(value) for key, value in attrs.items()}


@dataclass
class NodeSpec:
    id: str
    attrs: Dict[str, Any]

    def handler_type(self) -> str:
        explicit = self.attrs.get("type")
        if explicit:
            return str(explicit)
        shape = self.attrs.get("shape", "box")
        return SHAPE_TYPE_MAP.get(shape, "codergen")


@dataclass
class EdgeSpec:
    source: str
    target: str
    attrs: Dict[str, Any]


SHAPE_TYPE_MAP = {
    "Mdiamond": "start",
    "Msquare": "exit",
    "box": "codergen",
    "hexagon": "wait.human",
    "diamond": "conditional",
    "component": "parallel",
    "tripleoctagon": "parallel.fan_in",
    "parallelogram": "tool",
    "house": "stack.manager_loop",
}


class GraphSpec:
    """Parsed representation of an Attractor pipeline."""

    def __init__(
        self,
        nodes: Iterable[NodeSpec],
        edges: Iterable[EdgeSpec],
        graph_attrs: Mapping[str, Any],
    ) -> None:
        self.graph_attrs = dict(graph_attrs)
        self.nodes = {node.id: node for node in nodes}
        self.edges = list(edges)
        self._outgoing: Dict[str, List[EdgeSpec]] = {}
        for edge in self.edges:
            self._outgoing.setdefault(edge.source, []).append(edge)

    @classmethod
    def parse_dot_file(cls, path: Path | str) -> "GraphSpec":
        return cls.parse_dot_data(Path(path).read_text())

    @classmethod
    def parse_dot_data(cls, data: str) -> "GraphSpec":
        graphs = pydot.graph_from_dot_data(data)
        if not graphs:
            raise ValueError("DOT parser returned no graphs")
        graph = graphs[0]
        if graph.get_type() != "digraph":
            raise ValueError("Only digraphs are supported")
        nodes = []
        for node in graph.get_nodes():
            name = node.get_name().strip('"')
            if name in {"node", "edge", "graph"}:
                continue
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                raise ValueError(f"Invalid node id '{name}'")
            nodes.append(NodeSpec(id=name, attrs=_parse_attrs(node.get_attributes())))
        edges = []
        for raw in graph.get_edges():
            # pydot returns parsed edges with proper source/target
            source = raw.get_source().strip('"')
            destination = raw.get_destination().strip('"')
            edges.append(
                EdgeSpec(
                    source=source,
                    target=destination,
                    attrs=_parse_attrs(raw.get_attributes()),
                )
            )
        graph_attrs = _parse_attrs(graph.get_attributes())
        return cls(nodes=nodes, edges=edges, graph_attrs=graph_attrs)

    def outgoing(self, node_id: str) -> List[EdgeSpec]:
        return list(self._outgoing.get(node_id, []))

    def start_node(self) -> str:
        start_nodes = [node.id for node in self.nodes.values() if node.handler_type() == "start"]
        if len(start_nodes) != 1:
            raise ValueError("Graph must have exactly one start node (shape=Mdiamond)")
        return start_nodes[0]

    def exit_node(self) -> str:
        exit_nodes = [node.id for node in self.nodes.values() if node.handler_type() == "exit"]
        if len(exit_nodes) != 1:
            raise ValueError("Graph must have exactly one exit node (shape=Msquare)")
        return exit_nodes[0]

    def goal(self) -> str:
        return str(self.graph_attrs.get("goal", ""))

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def get_node(self, node_id: str) -> NodeSpec:
        return self.nodes[node_id]
