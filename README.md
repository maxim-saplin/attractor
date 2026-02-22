# Attractor 

This repository contains [NLSpecs](#terminology) to build your own version of Attractor to create your own software factory.

Although bringing your own agentic loop and unified LLM SDK is not required to build your own Attractor, we highly recommend controlling the stack so you have a strong foundation.

## Specs

- [Attractor Specification](./attractor-spec.md)
- [Coding Agent Loop Specification](./coding-agent-loop-spec.md)
- [Unified LLM Client Specification](./unified-llm-spec.md)

## Building Attractor

Supply the following prompt to a modern coding agent (Claude Code, Codex, OpenCode, Amp, Cursor, etc):

```
codeagent> Implement Attractor as described by https://github.com/strongdm/attractor
```

## Terminology

- **NLSpec** (Natural Language Spec): a human-readable spec intended to be  directly usable by coding agents to implement/validate behavior.

## Getting Started

1. Create a virtual environment at the repository root so tooling runs consistently:

   ```bash
   python3 -m virtualenv .venv
   ```

2. Activate the environment and install the project + dev dependencies:

   ```bash
   source .venv/bin/activate
   pip install -e ."[dev]"
   ```

3. Pipelines are defined as DOT files that use the constrained subset described in `attractor-spec.md`.

## Running pipelines

Use the `attractor` CLI entry point that wraps the engine, context store, and stubbed LLM:

```bash
.venv/bin/attractor path/to/pipeline.dot
```

Pass `-C key=value` multiple times to seed context or use `--skip-report` to suppress the summary output in automation.

## Testing

Tests exercise the DOT parser and engine described in the spec. Run them inside the `.venv` using `uv`, which integrates tightly with `pytest`:

```bash
.venv/bin/uv tests
```

`uv` will discover the test suite and print concise results; rerun the command after making changes to ensure regressions are caught.
