"""YAML agent loader — auto-discovers agents from a folder structure.

Each agent lives in its own subfolder with an ``agent.yaml`` file and an
optional Jinja2 prompt template.  A shared ``_defaults.yaml`` provides
global defaults that are deep-merged with each agent's config.

Expected folder structure::

    agents/
    ├── _defaults.yaml          # Global defaults (optional)
    ├── concierge/
    │   ├── agent.yaml          # Agent configuration
    │   └── prompt.jinja        # System prompt template
    ├── fraud_agent/
    │   ├── agent.yaml
    │   └── prompt.jinja
    └── ...

Example ``_defaults.yaml``::

    model:
      model: gpt-4o
      temperature: 0.7
      max_tokens: 4096

    template_vars:
      institution_name: "Contoso Bank"

Example ``agent.yaml``::

    agent:
      name: FraudAgent
      description: "Fraud detection specialist"
      greeting: "Hello! I'm the fraud specialist."
      handoff:
        trigger: handoff_fraud_agent

    model:
      model: gpt-4o
      temperature: 0.3

    tools:
      - analyze_transactions
      - block_card

    prompts:
      path: prompt.jinja

Usage::

    from agentkit import AgentLoader, ToolRegistry

    registry = ToolRegistry()
    loader = AgentLoader(agents_dir="./agents", tool_registry=registry)
    agents = loader.discover()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

from agentkit.agent import Agent, HandoffConfig, ModelConfig, build_handoff_map

logger = structlog.get_logger(__name__)


class AgentLoader:
    """Auto-discovers and loads agents from a modular folder structure.

    :param agents_dir: Path to the agents directory.
    :param tool_registry: Optional tool registry for validation.
    """

    def __init__(
        self,
        agents_dir: str | Path,
        tool_registry: Any | None = None,
    ) -> None:
        self._agents_dir = Path(agents_dir)
        self._tool_registry = tool_registry
        self._defaults: dict[str, Any] = {}

    def discover(self) -> dict[str, Agent]:
        """Scan the agents directory and load all ``agent.yaml`` files.

        :return: Dict of ``agent_name → Agent``.
        """
        self._defaults = self._load_defaults()
        agents: dict[str, Agent] = {}

        if not self._agents_dir.exists():
            logger.warning("agents_dir_not_found", path=str(self._agents_dir))
            return agents

        for item in sorted(self._agents_dir.iterdir()):
            if not item.is_dir():
                continue
            if item.name.startswith(("_", ".")):
                continue
            if item.name in ("__pycache__",):
                continue

            agent_file = item / "agent.yaml"
            if not agent_file.exists():
                continue

            try:
                agent = self._load_agent(agent_file)
                agents[agent.name] = agent
                logger.debug("agent_loaded", agent=agent.name, dir=item.name)
            except Exception as exc:
                logger.error(
                    "agent_load_failed", dir=item.name, error=str(exc)
                )

        logger.info(
            "agents_discovered",
            count=len(agents),
            names=list(agents.keys()),
        )
        return agents

    def build_handoff_map(self, agents: dict[str, Agent]) -> dict[str, str]:
        """Build a handoff map from discovered agents.

        :param agents: Dict of ``agent_name → Agent``.
        :return: Dict of ``tool_name → agent_name``.
        """
        return build_handoff_map(agents)

    def get_agent(self, name: str) -> Agent | None:
        """Load a single agent by name.

        :param name: Agent name (must match a subfolder name).
        :return: The loaded agent, or ``None`` if not found.
        """
        agents = self.discover()
        return agents.get(name)

    def list_agent_names(self) -> list[str]:
        """List all discovered agent names."""
        return list(self.discover().keys())

    # ── Private helpers ─────────────────────────────────────────────

    def _load_defaults(self) -> dict[str, Any]:
        """Load ``_defaults.yaml`` from the agents directory."""
        defaults_file = self._agents_dir / "_defaults.yaml"
        if defaults_file.exists():
            with open(defaults_file) as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_agent(self, agent_file: Path) -> Agent:
        """Load a single agent from its ``agent.yaml`` file."""
        with open(agent_file) as f:
            raw = yaml.safe_load(f) or {}

        agent_dir = agent_file.parent

        # Extract identity (handles nested 'agent:' block)
        identity = self._extract_identity(raw, agent_dir)

        # Merge model config with defaults
        model_raw = _deep_merge(
            self._defaults.get("model", {}), raw.get("model", {})
        )

        # Merge template vars
        template_vars = _deep_merge(
            self._defaults.get("template_vars", {}),
            raw.get("template_vars", {}),
        )

        # Load prompt template
        prompt_template = self._extract_prompt(raw, agent_dir)

        # Extract handoff config
        handoff = self._extract_handoff(raw)

        return Agent(
            name=identity["name"],
            description=identity["description"],
            greeting=identity.get("greeting", ""),
            return_greeting=identity.get("return_greeting", ""),
            handoff=handoff,
            model=ModelConfig.from_dict(model_raw),
            prompt_template=prompt_template,
            tool_names=raw.get("tools", []),
            template_vars=template_vars,
            metadata=raw.get("metadata", {}),
            source_dir=agent_dir,
        )

    def _extract_identity(
        self, raw: dict[str, Any], agent_dir: Path
    ) -> dict[str, Any]:
        """Extract agent identity, supporting nested ``agent:`` block."""
        agent_block = raw.get("agent", {})
        return {
            "name": (
                agent_block.get("name")
                or raw.get("name")
                or agent_dir.name
            ),
            "description": (
                agent_block.get("description") or raw.get("description", "")
            ),
            "greeting": (
                agent_block.get("greeting") or raw.get("greeting", "")
            ),
            "return_greeting": (
                agent_block.get("return_greeting")
                or raw.get("return_greeting", "")
            ),
        }

    def _extract_prompt(self, raw: dict[str, Any], agent_dir: Path) -> str:
        """Extract prompt from multiple possible formats."""
        # Check 'prompts:' block
        prompts_block = raw.get("prompts", {})
        if prompts_block:
            if prompts_block.get("content"):
                return prompts_block["content"]
            if prompts_block.get("path"):
                return _load_prompt_file(agent_dir, prompts_block["path"])

        # Check top-level 'prompt:'
        if raw.get("prompt"):
            return _load_prompt_file(agent_dir, raw["prompt"])

        return ""

    def _extract_handoff(self, raw: dict[str, Any]) -> HandoffConfig:
        """Extract handoff configuration."""
        # New-style nested block
        agent_block = raw.get("agent", {})
        if "handoff" in agent_block:
            return HandoffConfig.from_dict(agent_block["handoff"])
        if "handoff" in raw:
            return HandoffConfig.from_dict(raw["handoff"])
        # Legacy top-level trigger
        if "handoff_trigger" in raw:
            return HandoffConfig(trigger=raw["handoff_trigger"])
        return HandoffConfig()

    def build_agent_summaries(
        self, agents: dict[str, Agent]
    ) -> list[dict[str, Any]]:
        """Build lightweight summaries for telemetry/UI.

        :param agents: Dict of ``agent_name → Agent``.
        :return: List of summary dicts.
        """
        summaries: list[dict[str, Any]] = []
        for name, agent in agents.items():
            summaries.append(
                {
                    "name": name,
                    "description": (agent.description or "")[:160],
                    "greeting": bool(agent.greeting),
                    "return_greeting": bool(agent.return_greeting),
                    "tool_count": len(agent.tool_names),
                    "tools_preview": agent.tool_names[:5],
                    "handoff_trigger": agent.handoff.trigger or None,
                    "model": agent.model.model,
                }
            )
        return summaries


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge *override* into *base* (override wins). Returns a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_prompt_file(agent_dir: Path, prompt_value: str) -> str:
    """Load prompt content from a file or inline string.

    Supported extensions: ``.jinja``, ``.md``, ``.txt``.
    """
    if not prompt_value:
        return ""

    if prompt_value.endswith((".jinja", ".md", ".txt")):
        prompt_file = agent_dir / prompt_value
        if prompt_file.exists():
            return prompt_file.read_text()
        logger.warning("prompt_file_not_found", path=str(prompt_file))
        return ""
    return prompt_value


__all__ = [
    "AgentLoader",
]
