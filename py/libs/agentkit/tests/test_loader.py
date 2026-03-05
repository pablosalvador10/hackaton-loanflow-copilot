"""Tests for agentkit.loader — AgentLoader YAML discovery."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import os

from agentkit.loader import AgentLoader, _deep_merge


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    """Create a temporary agents directory with sample agents."""
    agents = tmp_path / "agents"
    agents.mkdir()

    # _defaults.yaml
    defaults = agents / "_defaults.yaml"
    defaults.write_text(
        """
model:
  model: gpt-4o
  temperature: 0.7
  max_tokens: 4096

template_vars:
  institution_name: "Test Bank"
"""
    )

    # concierge agent
    concierge_dir = agents / "concierge"
    concierge_dir.mkdir()
    (concierge_dir / "agent.yaml").write_text(
        """
agent:
  name: Concierge
  description: "Main banking assistant"
  greeting: "Hello{{ ', ' + user_name if user_name else '' }}!"
  return_greeting: "Welcome back!"
  handoff:
    trigger: handoff_concierge
    is_entry_point: true

model:
  temperature: 0.5

tools:
  - get_balance
  - transfer_funds
  - handoff_fraud

prompts:
  path: prompt.jinja
"""
    )
    (concierge_dir / "prompt.jinja").write_text(
        "You are {{ agent_name }}, the main assistant at {{ institution_name }}."
    )

    # fraud agent
    fraud_dir = agents / "fraud_agent"
    fraud_dir.mkdir()
    (fraud_dir / "agent.yaml").write_text(
        """
agent:
  name: FraudAgent
  description: "Fraud detection specialist"
  handoff:
    trigger: handoff_fraud

model:
  model: gpt-4o-mini
  temperature: 0.2

tools:
  - analyze_transactions
  - block_card

prompts:
  content: "You are the fraud detection specialist."
"""
    )

    return agents


class TestAgentLoader:
    """AgentLoader discovery and loading."""

    def test_discover_agents(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        assert len(agents) == 2
        assert "Concierge" in agents
        assert "FraudAgent" in agents

    def test_agent_identity(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        concierge = agents["Concierge"]
        assert concierge.description == "Main banking assistant"
        assert concierge.greeting.startswith("Hello")

    def test_defaults_merged(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        concierge = agents["Concierge"]
        # Temperature overridden in agent.yaml
        assert concierge.model.temperature == 0.5
        # max_tokens from defaults
        assert concierge.model.max_tokens == 4096

    def test_template_vars_merged(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        concierge = agents["Concierge"]
        assert concierge.template_vars["institution_name"] == "Test Bank"

    def test_prompt_from_file(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        concierge = agents["Concierge"]
        assert "{{ agent_name }}" in concierge.prompt_template

    def test_prompt_inline(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        fraud = agents["FraudAgent"]
        assert "fraud detection specialist" in fraud.prompt_template

    def test_handoff_config(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        assert agents["Concierge"].handoff.trigger == "handoff_concierge"
        assert agents["Concierge"].handoff.is_entry_point is True
        assert agents["FraudAgent"].handoff.trigger == "handoff_fraud"

    def test_tool_names(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        assert agents["Concierge"].tool_names == [
            "get_balance",
            "transfer_funds",
            "handoff_fraud",
        ]

    def test_build_handoff_map(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        hmap = loader.build_handoff_map(agents)
        assert hmap == {
            "handoff_concierge": "Concierge",
            "handoff_fraud": "FraudAgent",
        }

    def test_get_agent(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agent = loader.get_agent("Concierge")
        assert agent is not None
        assert agent.name == "Concierge"

    def test_get_agent_not_found(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        assert loader.get_agent("NonExistent") is None

    def test_list_agent_names(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        names = loader.list_agent_names()
        assert set(names) == {"Concierge", "FraudAgent"}

    def test_build_agent_summaries(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        summaries = loader.build_agent_summaries(agents)
        assert len(summaries) == 2
        names = {s["name"] for s in summaries}
        assert names == {"Concierge", "FraudAgent"}

    def test_empty_dir(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        loader = AgentLoader(empty)
        assert loader.discover() == {}

    def test_nonexistent_dir(self, tmp_path: Path):
        loader = AgentLoader(tmp_path / "nope")
        assert loader.discover() == {}

    def test_skips_underscored_dirs(self, agents_dir: Path):
        (agents_dir / "__pycache__").mkdir()
        (agents_dir / "_internal").mkdir()
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        assert len(agents) == 2  # Only concierge and fraud

    def test_prompt_render_with_loaded_agent(self, agents_dir: Path):
        loader = AgentLoader(agents_dir)
        agents = loader.discover()
        concierge = agents["Concierge"]
        rendered = concierge.render_prompt()
        assert "Concierge" in rendered
        assert "Test Bank" in rendered


class TestDeepMerge:
    """_deep_merge helper."""

    def test_simple_merge(self):
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_override(self):
        assert _deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested_merge(self):
        base = {"model": {"temperature": 0.7, "max_tokens": 4096}}
        override = {"model": {"temperature": 0.3}}
        result = _deep_merge(base, override)
        assert result == {"model": {"temperature": 0.3, "max_tokens": 4096}}

    def test_empty_override(self):
        base = {"a": 1, "b": 2}
        assert _deep_merge(base, {}) == base

    def test_empty_base(self):
        override = {"a": 1}
        assert _deep_merge({}, override) == override
