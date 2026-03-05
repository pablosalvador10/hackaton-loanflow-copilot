"""Scenario configuration — defines agent collaboration graphs.

A *scenario* describes which agents participate in a conversation and how
handoffs route between them.  It is essentially a directed graph where nodes
are agents and edges are handoff rules.

Example ``scenario.yaml``::

    scenario:
      name: banking
      description: "Full-service banking scenario"
      start_agent: BankingConcierge

    agents:
      - BankingConcierge
      - FraudAgent
      - InvestmentAdvisor

    handoffs:
      - from: BankingConcierge
        to: FraudAgent
        tool: handoff_to_agent
        type: announced
        condition: "User reports suspicious activity"
      - from: BankingConcierge
        to: InvestmentAdvisor
        tool: handoff_to_agent
        type: discrete
        condition: "User asks about investments"

    generic_handoff:
      enabled: true

Usage::

    from agentkit import ScenarioLoader

    loader = ScenarioLoader("./scenarios")
    scenario = loader.load("banking")

    # Get handoff instructions for a specific agent
    instructions = scenario.build_handoff_instructions("BankingConcierge")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class HandoffEdge:
    """A directed edge in the agent handoff graph.

    :param from_agent: Source agent name.
    :param to_agent: Target agent name.
    :param tool: Tool name to invoke (e.g. ``"handoff_to_agent"``).
    :param type: ``"announced"`` (agent says "transferring you") or ``"discrete"`` (silent).
    :param condition: When this handoff should activate (injected into prompt).
    :param share_context: Whether to pass conversation context to the target.
    """

    from_agent: str
    to_agent: str
    tool: str = "handoff_to_agent"
    type: str = "announced"
    condition: str = ""
    share_context: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandoffEdge:
        """Create from a YAML-parsed dictionary."""
        return cls(
            from_agent=data.get("from", data.get("from_agent", "")),
            to_agent=data.get("to", data.get("to_agent", "")),
            tool=data.get("tool", "handoff_to_agent"),
            type=data.get("type", "announced"),
            condition=data.get("condition", data.get("handoff_condition", "")),
            share_context=data.get("share_context", True),
        )


@dataclass
class GenericHandoffConfig:
    """Configuration for the generic ``handoff_to_agent`` tool.

    :param enabled: Whether the generic handoff tool is available.
    :param require_context: Whether context must be provided.
    """

    enabled: bool = False
    require_context: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenericHandoffConfig:
        """Create from a YAML-parsed dictionary."""
        if not data:
            return cls()
        return cls(
            enabled=data.get("enabled", False),
            require_context=data.get("require_context", False),
        )


@dataclass
class ScenarioConfig:
    """Complete scenario configuration — an agent collaboration graph.

    :param name: Scenario name.
    :param description: Human-readable description.
    :param agents: List of agent names participating.
    :param start_agent: Entry-point agent name.
    :param handoffs: Directed handoff edges between agents.
    :param generic_handoff: Generic handoff configuration.
    :param template_vars: Global template variables for all agents.
    :param agent_defaults: Per-agent overrides (keyed by agent name).
    """

    name: str
    description: str = ""
    agents: list[str] = field(default_factory=list)
    start_agent: str = ""
    handoffs: list[HandoffEdge] = field(default_factory=list)
    generic_handoff: GenericHandoffConfig = field(
        default_factory=GenericHandoffConfig
    )
    template_vars: dict[str, Any] = field(default_factory=dict)
    agent_defaults: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Graph queries ───────────────────────────────────────────────

    def get_outgoing_handoffs(self, agent_name: str) -> list[HandoffEdge]:
        """Get all handoff edges leaving a given agent.

        :param agent_name: Source agent name.
        :return: List of outgoing edges.
        """
        return [h for h in self.handoffs if h.from_agent == agent_name]

    def get_incoming_handoffs(self, agent_name: str) -> list[HandoffEdge]:
        """Get all handoff edges arriving at a given agent.

        :param agent_name: Target agent name.
        :return: List of incoming edges.
        """
        return [h for h in self.handoffs if h.to_agent == agent_name]

    def build_handoff_map(self) -> dict[str, str]:
        """Build a ``{tool_name: target_agent}`` map from edges.

        Only works for named handoff tools (not ``handoff_to_agent``).

        :return: Dict of ``tool_name → agent_name``.
        """
        hmap: dict[str, str] = {}
        for edge in self.handoffs:
            if edge.tool != "handoff_to_agent":
                hmap[edge.tool] = edge.to_agent
        return hmap

    def build_handoff_instructions(self, agent_name: str) -> str:
        """Auto-generate prompt instructions for available handoffs.

        Produces a markdown block describing which agents the current
        agent can hand off to and under what conditions.

        :param agent_name: The source agent.
        :return: Markdown-formatted handoff instructions.
        """
        outgoing = self.get_outgoing_handoffs(agent_name)
        if not outgoing and not self.generic_handoff.enabled:
            return ""

        lines = [
            "## AVAILABLE HANDOFFS",
            "You can transfer the conversation to these specialists:",
            "",
        ]

        for edge in outgoing:
            lines.append(f"- **{edge.to_agent}**: {edge.condition}")
            if edge.tool == "handoff_to_agent":
                lines.append(
                    f'  → Call `handoff_to_agent(target_agent="{edge.to_agent}", '
                    f'reason="<reason>")`'
                )
            else:
                lines.append(f"  → Call `{edge.tool}(reason=\"<reason>\")`")
            lines.append("")

        if self.generic_handoff.enabled and not outgoing:
            lines.append(
                "Use the `handoff_to_agent` tool to route the user to the "
                "appropriate specialist when their request falls outside your "
                "expertise."
            )

        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioConfig:
        """Create from a YAML-parsed dictionary."""
        scenario_block = data.get("scenario", {})

        handoffs = [
            HandoffEdge.from_dict(h) for h in data.get("handoffs", [])
        ]
        generic = GenericHandoffConfig.from_dict(
            data.get("generic_handoff", {})
        )

        return cls(
            name=scenario_block.get("name", data.get("name", "")),
            description=scenario_block.get(
                "description", data.get("description", "")
            ),
            agents=data.get("agents", []),
            start_agent=scenario_block.get(
                "start_agent", data.get("start_agent", "")
            ),
            handoffs=handoffs,
            generic_handoff=generic,
            template_vars=data.get("template_vars", {}),
            agent_defaults=data.get("agent_defaults", {}),
            metadata=data.get("metadata", {}),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO LOADER
# ═══════════════════════════════════════════════════════════════════════════════


class ScenarioLoader:
    """Loads scenario configurations from YAML files.

    :param scenarios_dir: Path to the directory containing scenario YAML files.
    """

    def __init__(self, scenarios_dir: str | Path) -> None:
        self._scenarios_dir = Path(scenarios_dir)

    def load(self, name: str) -> ScenarioConfig:
        """Load a scenario by name.

        Looks for ``<name>.yaml`` or ``<name>/scenario.yaml`` in the
        scenarios directory.

        :param name: Scenario name.
        :return: Parsed scenario config.
        :raises FileNotFoundError: If the scenario file doesn't exist.
        """
        # Try direct file first
        for candidate in [
            self._scenarios_dir / f"{name}.yaml",
            self._scenarios_dir / name / "scenario.yaml",
            self._scenarios_dir / name / "orchestration.yaml",
        ]:
            if candidate.exists():
                return self._load_file(candidate)

        raise FileNotFoundError(
            f"Scenario '{name}' not found in {self._scenarios_dir}. "
            f"Expected {name}.yaml or {name}/scenario.yaml"
        )

    def discover(self) -> dict[str, ScenarioConfig]:
        """Discover all scenarios in the scenarios directory.

        :return: Dict of ``scenario_name → ScenarioConfig``.
        """
        scenarios: dict[str, ScenarioConfig] = {}
        if not self._scenarios_dir.exists():
            return scenarios

        for item in sorted(self._scenarios_dir.iterdir()):
            try:
                if item.is_file() and item.suffix == ".yaml":
                    scenario = self._load_file(item)
                    scenarios[scenario.name] = scenario
                elif item.is_dir():
                    for name in ("scenario.yaml", "orchestration.yaml"):
                        candidate = item / name
                        if candidate.exists():
                            scenario = self._load_file(candidate)
                            scenarios[scenario.name] = scenario
                            break
            except Exception as exc:
                logger.error(
                    "scenario_load_failed", path=str(item), error=str(exc)
                )

        logger.info(
            "scenarios_discovered",
            count=len(scenarios),
            names=list(scenarios.keys()),
        )
        return scenarios

    def _load_file(self, path: Path) -> ScenarioConfig:
        """Load and parse a scenario YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        scenario = ScenarioConfig.from_dict(data)
        if not scenario.name:
            scenario.name = path.stem
        logger.debug("scenario_loaded", name=scenario.name, path=str(path))
        return scenario


__all__ = [
    "HandoffEdge",
    "GenericHandoffConfig",
    "ScenarioConfig",
    "ScenarioLoader",
]
