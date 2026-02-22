"""Smoke tests for the Attractor pipeline engine."""

from attractor.agent.loop import CodingAgentLoop
from attractor.core.context import Context
from attractor.core.engine import PipelineEngine
from attractor.core.graph import GraphSpec
from attractor.core.handlers import build_default_registry
from attractor.unified_llm.client import Client
from attractor.unified_llm.providers import StubProviderAdapter


SIMPLE_GRAPH = """
digraph pipeline {
    goal="demo goal";
    start [shape=Mdiamond];
    work [shape=box, prompt="Produce a summary"];
    exit [shape=Msquare];
    start -> work;
    work -> exit;
}
"""


def _engine_with_stub() -> PipelineEngine:
    client = Client(providers={"stub": StubProviderAdapter()}, default_provider="stub")
    loop = CodingAgentLoop(client)
    registry = build_default_registry(loop)
    return PipelineEngine(registry)


def test_parse_dot_data() -> None:
    graph = GraphSpec.parse_dot_data(SIMPLE_GRAPH)
    assert graph.start_node() == "start"
    assert graph.exit_node() == "exit"
    assert graph.goal() == "demo goal"


def test_engine_runs_simple_graph() -> None:
    graph = GraphSpec.parse_dot_data(SIMPLE_GRAPH)
    engine = _engine_with_stub()
    context = Context()
    result = engine.run(graph, context)
    assert "start" in result.completed_nodes
    assert "work" in result.completed_nodes
    assert "exit" in result.completed_nodes
    assert context.get("last_response") is not None
