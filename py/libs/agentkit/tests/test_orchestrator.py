"""Tests for agentkit.orchestrator — Orchestrator run/stream logic."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentkit.agent import Agent, HandoffConfig, ModelConfig
from agentkit.orchestrator import (
    Orchestrator,
    OrchestratorResult,
    StreamEvent,
    TurnContext,
)
from agentkit.registry import ToolRegistry
from agentkit.scenario import ScenarioConfig, HandoffEdge


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _make_agent(
    name: str,
    *,
    prompt: str = "You are {{ agent_name }}.",
    tools: list[str] | None = None,
    is_entry: bool = False,
    trigger: str = "",
) -> Agent:
    return Agent(
        name=name,
        description=f"Agent {name}",
        prompt_template=prompt,
        tool_names=tools or [],
        handoff=HandoffConfig(
            trigger=trigger or f"handoff_{name.lower()}",
            is_entry_point=is_entry,
        ),
        model=ModelConfig(model="gpt-4o-test"),
    )


def _mock_completion(text: str, tool_calls: list | None = None):
    """Create a mock ChatCompletion response."""
    message = MagicMock()
    message.content = text
    message.tool_calls = tool_calls
    message.model_dump.return_value = {
        "role": "assistant",
        "content": text,
        "tool_calls": None,
    }

    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "stop" if not tool_calls else "tool_calls"

    response = MagicMock()
    response.choices = [choice]
    return response


def _mock_tool_call(tool_call_id: str, name: str, args: dict) -> MagicMock:
    """Create a mock tool call from LLM response."""
    tc = MagicMock()
    tc.id = tool_call_id
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = json.dumps(args)
    return tc


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestTurnContext:
    def test_defaults(self):
        ctx = TurnContext()
        assert ctx.system_vars == {}
        assert ctx.active_agent == ""
        assert ctx.visited_agents == set()
        assert ctx.handoff_history == []
        assert ctx.tool_outputs == {}


class TestOrchestratorResult:
    def test_defaults(self):
        result = OrchestratorResult(text="Hello", agent_name="TestAgent")
        assert result.text == "Hello"
        assert result.agent_name == "TestAgent"
        assert result.tool_calls == []
        assert result.handoff_occurred is False


class TestStreamEvent:
    def test_text_delta(self):
        ev = StreamEvent(type="text_delta", data="chunk")
        assert ev.type == "text_delta"
        assert ev.data == "chunk"

    def test_done(self):
        ev = StreamEvent(type="done", data="AgentA")
        assert ev.type == "done"


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestOrchestrator:
    @pytest.fixture
    def registry(self) -> ToolRegistry:
        reg = ToolRegistry()

        @reg.tool(name="get_balance")
        def get_balance(account_id: str) -> dict:
            """Get account balance.

            :param account_id: The account ID.
            """
            return {"balance": 1000.0, "currency": "USD"}

        @reg.tool(name="get_weather")
        def get_weather(city: str) -> dict:
            """Get weather for a city.

            :param city: City name.
            """
            return {"temp": 72, "condition": "sunny"}

        return reg

    @pytest.fixture
    def agents(self) -> dict[str, Agent]:
        return {
            "Concierge": _make_agent(
                "Concierge",
                tools=["get_balance", "get_weather"],
                is_entry=True,
            ),
            "Specialist": _make_agent(
                "Specialist",
                tools=["get_balance"],
                trigger="handoff_specialist",
            ),
        }

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        client = AsyncMock()
        return client

    def test_init_finds_entry_point(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        assert orch.active_agent == "Concierge"

    def test_switch_agent(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        orch.switch_agent("Specialist")
        assert orch.active_agent == "Specialist"
        assert "Specialist" in orch.visited_agents

    def test_switch_agent_invalid(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        with pytest.raises(ValueError, match="not found"):
            orch.switch_agent("NonExistent")

    def test_reset(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        orch.switch_agent("Specialist")
        orch.reset()
        assert orch.active_agent == "Concierge"
        assert orch.visited_agents == {"Concierge"}

    def test_start_agent_override(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        orch = Orchestrator(
            agents=agents,
            tool_registry=registry,
            client=mock_client,
            start_agent="Specialist",
        )
        assert orch.active_agent == "Specialist"

    @pytest.mark.asyncio
    async def test_run_simple_text(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_completion("Your balance is $1000.")
        )

        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        result = await orch.run("What's my balance?")

        assert result.text == "Your balance is $1000."
        assert result.agent_name == "Concierge"
        assert result.handoff_occurred is False

    @pytest.mark.asyncio
    async def test_run_with_tool_call(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        # First call: LLM requests tool call
        tool_call = _mock_tool_call(
            "tc_1", "get_balance", {"account_id": "123"}
        )
        first_response = _mock_completion("", tool_calls=[tool_call])

        # Second call: LLM returns text after tool result
        second_response = _mock_completion("Your balance is $1000.")

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[first_response, second_response]
        )

        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        result = await orch.run("What's my balance?")

        assert result.text == "Your balance is $1000."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "get_balance"
        assert result.tool_calls[0]["result"]["balance"] == 1000.0

    @pytest.mark.asyncio
    async def test_run_max_rounds_exceeded(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        # Always return tool calls
        tool_call = _mock_tool_call(
            "tc_loop", "get_balance", {"account_id": "123"}
        )
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_completion("", tool_calls=[tool_call])
        )

        orch = Orchestrator(
            agents=agents,
            tool_registry=registry,
            client=mock_client,
            max_tool_rounds=2,
        )
        result = await orch.run("Loop forever")

        assert "able to complete" in result.text.lower()
        assert len(result.tool_calls) == 2

    @pytest.mark.asyncio
    async def test_run_with_handoff(
        self,
        agents: dict[str, Agent],
        registry: ToolRegistry,
        mock_client: AsyncMock,
    ):
        # Register a handoff tool
        registry.register_handoff(
            name="handoff_specialist",
            target_agent="Specialist",
            description="Transfer to specialist",
        )
        agents["Concierge"].tool_names.append("handoff_specialist")

        # First call (Concierge): LLM requests handoff
        handoff_call = _mock_tool_call(
            "tc_ho", "handoff_specialist", {"reason": "Need specialist"}
        )
        first_response = _mock_completion("", tool_calls=[handoff_call])

        # Second call (Specialist): LLM returns text
        second_response = _mock_completion("I can help with that.")

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[first_response, second_response]
        )

        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        result = await orch.run("I need a specialist")

        assert result.handoff_occurred is True
        assert result.agent_name == "Specialist"
        assert result.text == "I can help with that."

    def test_handoff_map_built(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        # handoff map built from agents
        assert "handoff_concierge" in orch._handoff_map
        assert "handoff_specialist" in orch._handoff_map

    def test_scenario_handoff_map_merged(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        scenario = ScenarioConfig(
            name="test",
            agents=["Concierge", "Specialist"],
            start_agent="Concierge",
            handoffs=[
                HandoffEdge(
                    from_agent="Concierge",
                    to_agent="Specialist",
                    tool="escalate",
                )
            ],
        )
        orch = Orchestrator(
            agents=agents,
            tool_registry=registry,
            client=mock_client,
            scenario=scenario,
        )
        assert "escalate" in orch._handoff_map

    @pytest.mark.asyncio
    async def test_run_with_context(
        self, agents: dict[str, Agent], registry: ToolRegistry, mock_client: AsyncMock
    ):
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_completion("Hello, user!")
        )

        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=mock_client
        )
        result = await orch.run(
            "Hello", context={"user_name": "Alice"}
        )

        assert result.text == "Hello, user!"
        # Context should be passed to TurnContext
        assert result.context.system_vars.get("user_name") == "Alice"


class TestOrchestratorEntryPoint:
    """Edge cases for entry point detection."""

    def test_no_entry_point_uses_first(self):
        agents = {
            "Alpha": _make_agent("Alpha"),
            "Beta": _make_agent("Beta"),
        }
        registry = ToolRegistry()
        orch = Orchestrator(
            agents=agents, tool_registry=registry, client=AsyncMock()
        )
        assert orch.active_agent == "Alpha"

    def test_entry_point_from_scenario(self):
        agents = {
            "Alpha": _make_agent("Alpha"),
            "Beta": _make_agent("Beta"),
        }
        scenario = ScenarioConfig(
            name="test",
            agents=["Alpha", "Beta"],
            start_agent="Beta",
        )
        registry = ToolRegistry()
        orch = Orchestrator(
            agents=agents,
            tool_registry=registry,
            client=AsyncMock(),
            scenario=scenario,
        )
        assert orch.active_agent == "Beta"
