"""Handler registry and builtin node handlers."""

from __future__ import annotations

import shlex
import subprocess
from abc import ABC, abstractmethod
from typing import Dict

from attractor.agent.loop import CodingAgentLoop
from attractor.core.conditions import evaluate_condition
from attractor.core.context import Context
from attractor.core.graph import GraphSpec, NodeSpec, Duration
from attractor.core.outcome import Outcome, StageStatus


class Handler(ABC):
    """Interface implemented by every node handler."""

    @abstractmethod
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        """Run the node and return an outcome."""


class HandlerRegistry:
    """Lookup table for handlers by type name."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Handler] = {}

    def register(self, name: str, handler: Handler) -> None:
        self._handlers[name] = handler

    def handler_for(self, name: str) -> Handler:
        if name not in self._handlers:
            raise KeyError(f"No handler registered for type '{name}'")
        return self._handlers[name]


class StartHandler(Handler):
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        context.append_log("Pipeline started")
        return Outcome(status=StageStatus.SUCCESS, notes="Start node")


class ExitHandler(Handler):
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        context.append_log("Pipeline completed")
        return Outcome(status=StageStatus.SUCCESS, notes="Exit node")


class CodergenHandler(Handler):
    def __init__(self, agent_loop: CodingAgentLoop) -> None:
        self.agent_loop = agent_loop

    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        prompt_template = str(node.attrs.get("prompt") or node.attrs.get("label") or node.id)
        prompt = prompt_template.replace("$goal", graph.goal())
        response = self.agent_loop.run(prompt, context)
        context.append_log(f"{node.id}: {response}")
        return Outcome(
            status=StageStatus.SUCCESS,
            context_updates={"last_response": response},
            notes="LLM generation completed",
        )


class ConditionalHandler(Handler):
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        expression = node.attrs.get("condition")
        if expression is None:
            matches = True
        elif isinstance(expression, bool):
            matches = expression
        else:
            matches = evaluate_condition(str(expression), context, graph.graph_attrs)
        context.append_log(f"Conditional {node.id} evaluated to {matches}")
        context_updates: Dict[str, object] = {"last_condition": matches}
        return Outcome(status=StageStatus.SUCCESS, context_updates=context_updates)


class HumanGateHandler(Handler):
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        answer = context.get("human.gate.answer")
        if not answer:
            outgoing = graph.outgoing(node.id)
            labels = [edge.attrs.get("label") for edge in outgoing if edge.attrs.get("label")]
            answer = labels[0] if labels else "continue"
        preferred_label = str(answer)
        context.append_log(f"Human gate chose '{preferred_label}'")
        return Outcome(
            status=StageStatus.SUCCESS,
            preferred_label=preferred_label,
            context_updates={
                "human.gate.last_answer": preferred_label,
            },
        )


class ToolHandler(Handler):
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        command = node.attrs.get("tool_command")
        if not command:
            return Outcome(
                status=StageStatus.FAIL,
                failure_reason="tool_command attribute is missing",
            )
        context.append_log(f"Executing tool command: {command}")
        try:
            timeout_attr = node.attrs.get("timeout")
            if isinstance(timeout_attr, Duration):
                timeout_seconds = timeout_attr.to_seconds()
            elif timeout_attr is not None:
                timeout_seconds = float(timeout_attr)
            else:
                timeout_seconds = 10
            result = subprocess.run(
                shlex.split(str(command)),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover
            return Outcome(
                status=StageStatus.FAIL,
                failure_reason=str(exc),
            )
        context_updates = {
            "tool.output": result.stdout.strip(),
            "tool.stderr": result.stderr.strip(),
        }
        if result.returncode != 0:
            return Outcome(
                status=StageStatus.FAIL,
                context_updates=context_updates,
                failure_reason=f"Command exited {result.returncode}",
            )
        return Outcome(
            status=StageStatus.SUCCESS,
            context_updates=context_updates,
            notes=f"Command completed with {len(result.stdout.strip())} bytes",
        )


class ParallelHandler(Handler):
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        context.append_log("Parallel node executed (branches will be evaluated sequentially)")
        branches = ",".join(str(edge.target) for edge in graph.outgoing(node.id))
        return Outcome(
            status=StageStatus.SUCCESS,
            context_updates={f"parallel.{node.id}.branches": branches},
        )


class ParallelFanInHandler(Handler):
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        context.append_log("Parallel fan-in node reached")
        return Outcome(status=StageStatus.SUCCESS, notes="Fan-in merged branches")


class ManagerLoopHandler(Handler):
    def execute(self, node: NodeSpec, context: Context, graph: GraphSpec) -> Outcome:
        context.append_log("Manager loop handler observed")
        return Outcome(status=StageStatus.SUCCESS, notes="Manager loop step")


def build_default_registry(agent_loop: CodingAgentLoop) -> HandlerRegistry:
    registry = HandlerRegistry()
    registry.register("start", StartHandler())
    registry.register("exit", ExitHandler())
    registry.register("codergen", CodergenHandler(agent_loop))
    registry.register("wait.human", HumanGateHandler())
    registry.register("conditional", ConditionalHandler())
    registry.register("tool", ToolHandler())
    registry.register("parallel", ParallelHandler())
    registry.register("parallel.fan_in", ParallelFanInHandler())
    registry.register("stack.manager_loop", ManagerLoopHandler())
    return registry
