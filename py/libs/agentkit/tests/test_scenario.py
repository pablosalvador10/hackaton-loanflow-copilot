"""Tests for agentkit.scenario — ScenarioConfig & ScenarioLoader."""

from __future__ import annotations

import pytest
from pathlib import Path

from agentkit.scenario import (
    HandoffEdge,
    GenericHandoffConfig,
    ScenarioConfig,
    ScenarioLoader,
)


# ── HandoffEdge ─────────────────────────────────────────────────────────


class TestHandoffEdge:
    def test_from_dict_basic(self):
        edge = HandoffEdge.from_dict(
            {"from": "A", "to": "B", "condition": "User asks about B"}
        )
        assert edge.from_agent == "A"
        assert edge.to_agent == "B"
        assert edge.tool == "handoff_to_agent"
        assert edge.type == "announced"
        assert edge.condition == "User asks about B"
        assert edge.share_context is True

    def test_from_dict_named_tool(self):
        edge = HandoffEdge.from_dict(
            {"from_agent": "A", "to_agent": "B", "tool": "transfer_to_b"}
        )
        assert edge.from_agent == "A"
        assert edge.to_agent == "B"
        assert edge.tool == "transfer_to_b"

    def test_from_dict_discrete(self):
        edge = HandoffEdge.from_dict(
            {
                "from": "A",
                "to": "B",
                "type": "discrete",
                "share_context": False,
            }
        )
        assert edge.type == "discrete"
        assert edge.share_context is False


# ── GenericHandoffConfig ────────────────────────────────────────────────


class TestGenericHandoffConfig:
    def test_defaults(self):
        cfg = GenericHandoffConfig()
        assert cfg.enabled is False
        assert cfg.require_context is False

    def test_from_dict_enabled(self):
        cfg = GenericHandoffConfig.from_dict({"enabled": True})
        assert cfg.enabled is True

    def test_from_dict_empty(self):
        cfg = GenericHandoffConfig.from_dict({})
        assert cfg.enabled is False

    def test_from_dict_none(self):
        cfg = GenericHandoffConfig.from_dict(None)
        assert cfg.enabled is False


# ── ScenarioConfig ──────────────────────────────────────────────────────


class TestScenarioConfig:
    @pytest.fixture
    def scenario_data(self) -> dict:
        return {
            "scenario": {
                "name": "banking",
                "description": "Full-service banking",
                "start_agent": "Concierge",
            },
            "agents": ["Concierge", "FraudAgent", "Advisor"],
            "handoffs": [
                {
                    "from": "Concierge",
                    "to": "FraudAgent",
                    "tool": "handoff_fraud",
                    "condition": "Suspicious activity detected",
                },
                {
                    "from": "Concierge",
                    "to": "Advisor",
                    "tool": "handoff_to_agent",
                    "type": "discrete",
                    "condition": "Investment questions",
                },
            ],
            "generic_handoff": {"enabled": True},
            "template_vars": {"bank_name": "Test Bank"},
        }

    def test_from_dict(self, scenario_data: dict):
        sc = ScenarioConfig.from_dict(scenario_data)
        assert sc.name == "banking"
        assert sc.start_agent == "Concierge"
        assert len(sc.handoffs) == 2
        assert sc.generic_handoff.enabled is True
        assert sc.template_vars["bank_name"] == "Test Bank"

    def test_get_outgoing_handoffs(self, scenario_data: dict):
        sc = ScenarioConfig.from_dict(scenario_data)
        out = sc.get_outgoing_handoffs("Concierge")
        assert len(out) == 2
        assert out[0].to_agent == "FraudAgent"
        assert out[1].to_agent == "Advisor"

    def test_get_incoming_handoffs(self, scenario_data: dict):
        sc = ScenarioConfig.from_dict(scenario_data)
        inc = sc.get_incoming_handoffs("FraudAgent")
        assert len(inc) == 1
        assert inc[0].from_agent == "Concierge"

    def test_get_outgoing_handoffs_none(self, scenario_data: dict):
        sc = ScenarioConfig.from_dict(scenario_data)
        assert sc.get_outgoing_handoffs("FraudAgent") == []

    def test_build_handoff_map(self, scenario_data: dict):
        sc = ScenarioConfig.from_dict(scenario_data)
        hmap = sc.build_handoff_map()
        # Only named tools (not handoff_to_agent) appear
        assert hmap == {"handoff_fraud": "FraudAgent"}

    def test_build_handoff_instructions(self, scenario_data: dict):
        sc = ScenarioConfig.from_dict(scenario_data)
        instructions = sc.build_handoff_instructions("Concierge")
        assert "## AVAILABLE HANDOFFS" in instructions
        assert "FraudAgent" in instructions
        assert "Advisor" in instructions
        assert "handoff_fraud" in instructions
        assert "handoff_to_agent" in instructions

    def test_build_handoff_instructions_no_handoffs(self):
        sc = ScenarioConfig(name="empty", agents=["Solo"])
        assert sc.build_handoff_instructions("Solo") == ""

    def test_build_handoff_instructions_generic_only(self):
        sc = ScenarioConfig(
            name="generic",
            agents=["Solo"],
            generic_handoff=GenericHandoffConfig(enabled=True),
        )
        instr = sc.build_handoff_instructions("Solo")
        assert "handoff_to_agent" in instr

    def test_from_dict_minimal(self):
        sc = ScenarioConfig.from_dict({"scenario": {"name": "minimal"}})
        assert sc.name == "minimal"
        assert sc.agents == []
        assert sc.handoffs == []


# ── ScenarioLoader ──────────────────────────────────────────────────────


class TestScenarioLoader:
    @pytest.fixture
    def scenarios_dir(self, tmp_path: Path) -> Path:
        sdir = tmp_path / "scenarios"
        sdir.mkdir()

        # Direct file
        (sdir / "banking.yaml").write_text(
            """
scenario:
  name: banking
  start_agent: Teller
agents:
  - Teller
  - Manager
handoffs:
  - from: Teller
    to: Manager
    condition: "Escalation needed"
"""
        )

        # Subdirectory
        sub = sdir / "insurance"
        sub.mkdir()
        (sub / "scenario.yaml").write_text(
            """
scenario:
  name: insurance
  start_agent: ClaimsAgent
agents:
  - ClaimsAgent
"""
        )
        return sdir

    def test_load_direct_file(self, scenarios_dir: Path):
        loader = ScenarioLoader(scenarios_dir)
        sc = loader.load("banking")
        assert sc.name == "banking"
        assert sc.start_agent == "Teller"
        assert len(sc.handoffs) == 1

    def test_load_subdirectory(self, scenarios_dir: Path):
        loader = ScenarioLoader(scenarios_dir)
        sc = loader.load("insurance")
        assert sc.name == "insurance"

    def test_load_not_found(self, scenarios_dir: Path):
        loader = ScenarioLoader(scenarios_dir)
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            loader.load("nonexistent")

    def test_discover(self, scenarios_dir: Path):
        loader = ScenarioLoader(scenarios_dir)
        scenarios = loader.discover()
        assert len(scenarios) == 2
        assert "banking" in scenarios
        assert "insurance" in scenarios

    def test_discover_empty(self, tmp_path: Path):
        loader = ScenarioLoader(tmp_path / "empty")
        assert loader.discover() == {}
