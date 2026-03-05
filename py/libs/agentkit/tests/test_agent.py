"""Tests for agentkit.agent — Agent dataclass and helpers."""

from __future__ import annotations

import pytest

from agentkit.agent import Agent, HandoffConfig, ModelConfig, build_handoff_map


class TestHandoffConfig:
    """HandoffConfig creation and serialisation."""

    def test_defaults(self):
        cfg = HandoffConfig()
        assert cfg.trigger == ""
        assert cfg.is_entry_point is False

    def test_from_dict(self):
        cfg = HandoffConfig.from_dict(
            {"trigger": "handoff_fraud", "is_entry_point": True}
        )
        assert cfg.trigger == "handoff_fraud"
        assert cfg.is_entry_point is True

    def test_from_dict_empty(self):
        cfg = HandoffConfig.from_dict({})
        assert cfg.trigger == ""

    def test_from_dict_none(self):
        cfg = HandoffConfig.from_dict(None)
        assert cfg.trigger == ""


class TestModelConfig:
    """ModelConfig creation and serialisation."""

    def test_defaults(self):
        cfg = ModelConfig()
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 4096

    def test_from_dict(self):
        cfg = ModelConfig.from_dict(
            {"model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 2048}
        )
        assert cfg.model == "gpt-4o-mini"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 2048

    def test_from_dict_deployment_id_alias(self):
        """The ``deployment_id`` key should map to ``model``."""
        cfg = ModelConfig.from_dict({"deployment_id": "my-deployment"})
        assert cfg.model == "my-deployment"

    def test_to_dict_roundtrip(self):
        original = ModelConfig(model="gpt-4o", temperature=0.5)
        data = original.to_dict()
        restored = ModelConfig.from_dict(data)
        assert restored.model == original.model
        assert restored.temperature == original.temperature


class TestAgent:
    """Agent dataclass rendering and helpers."""

    def test_render_prompt_basic(self):
        agent = Agent(
            name="TestBot",
            prompt_template="Hello, I am {{ agent_name }}.",
        )
        result = agent.render_prompt()
        assert "TestBot" in result

    def test_render_prompt_with_context(self):
        agent = Agent(
            name="TestBot",
            prompt_template="Hello {{ user_name }}, I am {{ agent_name }}.",
        )
        result = agent.render_prompt({"user_name": "Alice"})
        assert "Alice" in result
        assert "TestBot" in result

    def test_render_prompt_filters_none(self):
        agent = Agent(
            name="TestBot",
            prompt_template="Hello {{ user_name | default('friend') }}.",
        )
        result = agent.render_prompt({"user_name": None})
        assert "friend" in result

    def test_render_prompt_with_template_vars(self):
        agent = Agent(
            name="TestBot",
            prompt_template="Welcome to {{ institution }}.",
            template_vars={"institution": "Contoso Bank"},
        )
        result = agent.render_prompt()
        assert "Contoso Bank" in result

    def test_render_prompt_context_overrides_template_vars(self):
        agent = Agent(
            name="TestBot",
            prompt_template="Institution: {{ institution }}.",
            template_vars={"institution": "Default Bank"},
        )
        result = agent.render_prompt({"institution": "Override Bank"})
        assert "Override Bank" in result

    def test_render_greeting(self):
        agent = Agent(
            name="TestBot",
            greeting="Hello {{ user_name | default('there') }}!",
        )
        assert agent.render_greeting({"user_name": "Bob"}) == "Hello Bob!"
        assert agent.render_greeting() == "Hello there!"

    def test_render_greeting_none_when_empty(self):
        agent = Agent(name="TestBot")
        assert agent.render_greeting() is None

    def test_render_return_greeting(self):
        agent = Agent(
            name="TestBot",
            return_greeting="Welcome back, {{ user_name }}!",
        )
        result = agent.render_return_greeting({"user_name": "Alice"})
        assert result == "Welcome back, Alice!"

    def test_get_handoff_tool_names(self):
        agent = Agent(
            name="TestBot",
            tool_names=[
                "get_balance",
                "handoff_fraud",
                "handoff_support",
                "search",
            ],
        )
        handoffs = agent.get_handoff_tool_names()
        assert handoffs == ["handoff_fraud", "handoff_support"]

    def test_is_handoff_target(self):
        agent = Agent(
            name="FraudBot",
            handoff=HandoffConfig(trigger="handoff_fraud"),
        )
        assert agent.is_handoff_target("handoff_fraud") is True
        assert agent.is_handoff_target("handoff_support") is False

    def test_repr(self):
        agent = Agent(
            name="TestBot",
            tool_names=["a", "b"],
            handoff=HandoffConfig(trigger="handoff_test"),
        )
        r = repr(agent)
        assert "TestBot" in r
        assert "tools=2" in r

    def test_invalidate_tool_cache(self):
        agent = Agent(name="TestBot")
        agent._cached_tools = [{"fake": True}]
        agent.invalidate_tool_cache()
        assert agent._cached_tools is None


class TestBuildHandoffMap:
    """build_handoff_map function."""

    def test_builds_map(self):
        agents = {
            "Concierge": Agent(
                name="Concierge",
                handoff=HandoffConfig(trigger="handoff_concierge", is_entry_point=True),
            ),
            "Fraud": Agent(
                name="Fraud",
                handoff=HandoffConfig(trigger="handoff_fraud"),
            ),
            "NoHandoff": Agent(name="NoHandoff"),
        }
        hmap = build_handoff_map(agents)
        assert hmap == {
            "handoff_concierge": "Concierge",
            "handoff_fraud": "Fraud",
        }

    def test_empty_agents(self):
        assert build_handoff_map({}) == {}
