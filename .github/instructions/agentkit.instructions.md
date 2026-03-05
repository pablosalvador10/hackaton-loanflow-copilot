---
applyTo: "py/libs/agentkit/**"
---

# Agentkit Library Instructions

These instructions apply when working with files in `py/libs/agentkit/`.

## Overview

**agentkit** is a YAML-driven, local multi-agent framework that uses the OpenAI Chat Completions API (or any compatible API). It is an alternative to **foundrykit** (which wraps Azure AI Foundry SDK for remote agents). Both libraries coexist — agents can be created using either approach.

## Architecture

| Module | Purpose |
|--------|---------|
| `agent.py` | `Agent`, `HandoffConfig`, `ModelConfig` dataclasses — orchestrator-agnostic agent definition |
| `registry.py` | `ToolRegistry` — decorator & imperative tool registration, auto-schema from type hints |
| `loader.py` | `AgentLoader` — YAML discovery with `_defaults.yaml` deep-merge |
| `scenario.py` | `ScenarioConfig`, `HandoffEdge` — directed handoff graphs |
| `orchestrator.py` | `Orchestrator` — multi-agent loop with `run()` and `stream()` |

## Key Design Patterns (from ART Voice Agent Accelerator)

- **Agent = pure config** — `Agent` is a dataclass with no orchestration logic.
- **YAML-first** — agents are defined in `agent.yaml` files under per-agent directories.
- **`_defaults.yaml`** — provides base config deep-merged into each agent.
- **Jinja2 prompts** — `prompt.jinja` / `prompt.md` files rendered with template vars.
- **Tool registry** — class-based `ToolRegistry` (not module-level singleton) for testability.
- **Scenario graphs** — `ScenarioConfig` defines handoff edges between agents.

## Critical Rules

1. **Every function MUST have:**
   - Complete type hints
   - Docstring with `:param`, `:return:`, `:raises:`
   - Error handling (try/except)
   - Structured logging via `structlog` (no `print()`)
2. **Tool functions registered via `@registry.tool()` MUST:**
   - Have type-annotated parameters (for auto-schema generation)
   - Have a docstring with `:param:` descriptions (for OpenAI function descriptions)
   - Return a `dict` (tool results are JSON-serialized)
3. **Agent YAML files MUST include** `agent.name`, `agent.description`, and a prompt (via `prompts.path` or `prompts.content`).
4. **Handoff tools** use `registry.register_handoff()` or `registry.register_generic_handoff()` — never register handoffs as regular tools.
5. **OpenTelemetry spans** wrap every tool execution (automatic via registry).

## File Layout for Agent Definitions

```
agents/
├── _defaults.yaml          # Global defaults (model config, template vars)
├── concierge/
│   ├── agent.yaml          # Agent identity, tools, handoff config
│   └── prompt.jinja        # System prompt (Jinja2 template)
├── fraud_agent/
│   ├── agent.yaml
│   └── prompt.md
└── scenarios/
    └── banking.yaml         # Scenario handoff graph
```

## Usage Pattern

```python
from agentkit import AgentLoader, Orchestrator, ToolRegistry, ScenarioLoader

# 1. Create registry and register tools
registry = ToolRegistry()

@registry.tool(tags={"banking"})
async def get_balance(account_id: str) -> dict:
    """Get account balance.
    :param account_id: The account ID.
    """
    return {"balance": 1000.0}

# 2. Load agents from YAML
loader = AgentLoader("./agents", tool_registry=registry)
agents = loader.discover()

# 3. Optionally load scenario
scenario_loader = ScenarioLoader("./agents/scenarios")
scenario = scenario_loader.load("banking")

# 4. Create orchestrator
orchestrator = Orchestrator(
    agents=agents,
    tool_registry=registry,
    scenario=scenario,
    model="gpt-4o",
)

# 5. Run
result = await orchestrator.run("What's my balance?")
```

## Dependency Management

- Package is at `py/libs/agentkit/` with its own `pyproject.toml`.
- Registered as a workspace member in `py/pyproject.toml`.
- Key deps: `openai`, `pydantic`, `pyyaml`, `jinja2`, `structlog`, `opentelemetry-api`.
- Install via `uv sync --all-packages` from `py/`.

## Testing

```bash
cd py && uv run pytest libs/agentkit/tests/ -v
```

Tests cover: `Agent`, `ToolRegistry`, `AgentLoader`, `ScenarioConfig`, `Orchestrator` (with mocked OpenAI client).

## Do / Don't

**Do:**
- Keep `Agent` as a pure dataclass — no I/O or orchestration logic in it.
- Use `ToolRegistry` class instances (not global state) for testability.
- Use `_defaults.yaml` for shared config to avoid YAML duplication.
- Write tests for new tools and agent configurations.

**Don't:**
- Mix foundrykit and agentkit patterns in the same agent — pick one approach.
- Add orchestration logic to `Agent` or `AgentLoader` — that belongs in `Orchestrator`.
- Use `print()` — use `structlog` for all logging.
- Create new `AsyncOpenAI` instances per request — reuse via `Orchestrator`.
