"""Command-line entry point for running Attractor pipelines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from attractor.agent.loop import CodingAgentLoop
from attractor.core.context import Context, context_from_pairs
from attractor.core.engine import PipelineEngine, RunResult
from attractor.core.graph import GraphSpec
from attractor.core.handlers import build_default_registry
from attractor.unified_llm.client import Client
from attractor.unified_llm.providers import StubProviderAdapter


def _build_agent_loop() -> CodingAgentLoop:
    client = Client(providers={"stub": StubProviderAdapter()}, default_provider="stub")
    return CodingAgentLoop(client)


def _report(result: RunResult, context: Context) -> None:
    print("Completed nodes:", ", ".join(result.completed_nodes))
    print("Goal gates satisfied:", result.goal_gate_satisfied)
    print("Events:")
    for event in result.events:
        print("  -", event)
    print("Final context snapshot:")
    print(json.dumps(context.snapshot(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="attractor")
    parser.add_argument("dot", type=Path, help="Path to the Attractor DOT workflow")
    parser.add_argument(
        "--context",
        "-C",
        action="append",
        default=[],
        help="Extra context entries (format key=value)",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip printing the final report (useful for automation)",
    )

    args = parser.parse_args()
    if not args.dot.exists():
        raise SystemExit(f"DOT file {args.dot} does not exist")
    graph = GraphSpec.parse_dot_file(args.dot)
    user_context = context_from_pairs(args.context)
    context = Context()
    context.update(user_context.snapshot())
    agent_loop = _build_agent_loop()
    registry = build_default_registry(agent_loop)
    engine = PipelineEngine(registry)
    result = engine.run(graph, context)
    if not args.skip_report:
        _report(result, context)
