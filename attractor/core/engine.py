"""Execution engine that walks the Attractor graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping

from attractor.core.conditions import evaluate_condition
from attractor.core.context import Context
from attractor.core.graph import EdgeSpec, GraphSpec, NodeSpec
from attractor.core.handlers import HandlerRegistry
from attractor.core.outcome import Outcome, StageStatus


@dataclass
class RunResult:
    completed_nodes: List[str] = field(default_factory=list)
    goal_gate_satisfied: bool = False
    context: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)


class PipelineEngine:
    """Orchestrates handler execution and edge routing."""

    def __init__(self, registry: HandlerRegistry) -> None:
        self.registry = registry

    def run(self, graph: GraphSpec, context: Context) -> RunResult:
        start = graph.start_node()
        exit_node = graph.exit_node()
        context.set("graph.goal", graph.goal())
        retries: Dict[str, int] = {}
        goal_gate_nodes = {
            node.id for node in graph.nodes.values() if node.attrs.get("goal_gate")
        }
        satisfied: set[str] = set()
        result = RunResult()
        current = start
        last_status = StageStatus.SUCCESS
        while True:
            node = graph.get_node(current)
            handler = self.registry.handler_for(node.handler_type())
            outcome = handler.execute(node, context, graph)
            result.events.append(
                {
                    "node": node.id,
                    "status": outcome.status.value,
                    "notes": outcome.notes,
                }
            )
            if outcome.context_updates:
                context.update(outcome.context_updates)
            if node.attrs.get("goal_gate") and outcome.status == StageStatus.SUCCESS:
                satisfied.add(node.id)
            result.completed_nodes.append(node.id)
            last_status = outcome.status
            if outcome.status in {StageStatus.FAIL, StageStatus.RETRY}:
                max_retries = int(node.attrs.get("max_retries", 0))
                retry_key = f"internal.retry_count.{node.id}"
                count = retries.get(node.id, 0)
                if count < max_retries:
                    retries[node.id] = count + 1
                    context.set(retry_key, count + 1)
                    continue
            if node.id == exit_node:
                break
            next_node = self._pick_next_node(node, graph, context, outcome)
            if next_node is None:
                raise RuntimeError(f"No eligible outgoing edge from '{node.id}'")
            current = next_node
        result.goal_gate_satisfied = not (goal_gate_nodes - satisfied)
        result.context = context.snapshot()
        return result

    def _pick_next_node(
        self,
        node: NodeSpec,
        graph: GraphSpec,
        context: Context,
        outcome: Outcome,
    ) -> str | None:
        if outcome.suggested_next_ids:
            for candidate in outcome.suggested_next_ids:
                if graph.has_node(candidate):
                    return candidate
        if outcome.status == StageStatus.FAIL:
            retry_target = node.attrs.get("retry_target") or node.attrs.get("fallback_retry_target")
            if retry_target and graph.has_node(str(retry_target)):
                return str(retry_target)

        outgoing = graph.outgoing(node.id)
        candidates = [
            edge
            for edge in outgoing
            if evaluate_condition(edge.attrs.get("condition"), context, graph.graph_attrs)
        ]
        if not candidates:
            return None
        preferred = outcome.preferred_label
        if preferred:
            for edge in candidates:
                label = edge.attrs.get("label")
                if label and str(label) == preferred:
                    return edge.target
        weighted = sorted(candidates, key=lambda edge: int(edge.attrs.get("weight", 0)), reverse=True)
        return weighted[0].target
