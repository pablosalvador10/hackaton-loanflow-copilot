"""agentkit — YAML-driven multi-agent framework.

Provides a local-first approach to building AI agents using:

- **YAML agent definitions** with Jinja2 prompt templates
- **Global tool registry** with import-time registration
- **Multi-agent handoff orchestration** via directed graphs
- **Scenario configuration** for agent collaboration
- **Session management** with per-session overrides
- **OpenAI Chat Completions** as the execution backend

Architecture inspired by the ART Voice Agent Accelerator pattern:
agents are defined once in YAML, loaded into ``Agent`` dataclasses,
and consumed by an orchestrator that manages tool execution, handoffs,
and conversation flow.

Quick Start::

    from agentkit import Agent, ToolRegistry, AgentLoader, Orchestrator

    # 1. Register tools
    registry = ToolRegistry()

    @registry.tool()
    async def get_weather(city: str) -> dict:
        \"\"\"Get current weather for a city.\"\"\"
        return {"city": city, "temp": 72, "condition": "sunny"}

    # 2. Load agents from YAML
    loader = AgentLoader(agents_dir="./agents", tool_registry=registry)
    agents = loader.discover()

    # 3. Run orchestrator
    orchestrator = Orchestrator(agents=agents, tool_registry=registry)
    result = await orchestrator.run("What's the weather in Seattle?")

Alternatively, define agents in Python::

    from agentkit import Agent, ModelConfig

    agent = Agent(
        name="WeatherBot",
        description="Provides weather information",
        prompt_template="You are a helpful weather assistant.",
        tool_names=["get_weather"],
        model=ModelConfig(model="gpt-4o", temperature=0.7),
    )
"""

from __future__ import annotations

from agentkit.agent import Agent, HandoffConfig, ModelConfig
from agentkit.loader import AgentLoader
from agentkit.orchestrator import (
    Orchestrator,
    OrchestratorResult,
    TurnContext,
)
from agentkit.registry import ToolDefinition, ToolRegistry
from agentkit.scenario import HandoffEdge, ScenarioConfig, ScenarioLoader

__all__ = [
    # Core agent
    "Agent",
    "HandoffConfig",
    "ModelConfig",
    # Tool registry
    "ToolDefinition",
    "ToolRegistry",
    # Agent loading
    "AgentLoader",
    # Orchestration
    "Orchestrator",
    "OrchestratorResult",
    "TurnContext",
    # Scenarios
    "HandoffEdge",
    "ScenarioConfig",
    "ScenarioLoader",
]
