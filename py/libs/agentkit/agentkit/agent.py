"""Agent dataclass — orchestrator-agnostic agent definition.

Every agent in agentkit is represented as an ``Agent`` dataclass.  Agents are
defined once (in YAML or Python) and can be consumed by any orchestrator
without modification.

The agent stores its configuration (name, prompt template, tool names, model
settings, handoff config) but delegates actual tool execution and LLM calls
to the orchestrator or registry layer.

Key design principles (from the ART Voice Agent pattern):

1. **YAML → Dataclass → Orchestrator-Agnostic** — Agent is pure config.
2. **Jinja2 prompts** — Prompts are templates rendered at runtime with context.
3. **Handoff-aware** — Each agent declares which tool routes TO it.
4. **Deep-merge defaults** — Per-agent YAML overrides global ``_defaults.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
from jinja2 import Template

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class HandoffConfig:
    """Declares how other agents route TO this agent.

    :param trigger: Tool name that routes to this agent (e.g. ``"handoff_fraud_agent"``).
    :param is_entry_point: Whether this agent is the default starting agent.
    """

    trigger: str = ""
    is_entry_point: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HandoffConfig:
        """Create from a YAML-parsed dictionary."""
        if not data:
            return cls()
        return cls(
            trigger=data.get("trigger", ""),
            is_entry_point=data.get("is_entry_point", False),
        )


@dataclass
class ModelConfig:
    """LLM model configuration.

    :param model: Model name or deployment ID (e.g. ``"gpt-4o"``).
    :param temperature: Sampling temperature (0–2).
    :param top_p: Nucleus sampling probability.
    :param max_tokens: Maximum response tokens.
    """

    model: str = "gpt-4o"
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 4096

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        """Create from a YAML-parsed dictionary."""
        if not data:
            return cls()
        model = data.get("model", data.get("deployment_id", data.get("name", cls.model)))
        return cls(
            model=model,
            temperature=float(data.get("temperature", cls.temperature)),
            top_p=float(data.get("top_p", cls.top_p)),
            max_tokens=int(data.get("max_tokens", cls.max_tokens)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Agent:
    """Orchestrator-agnostic agent configuration.

    An ``Agent`` captures everything needed to configure an LLM-powered agent:
    identity, prompt template, tool list, model settings, and handoff config.

    The agent itself has **no orchestration logic** — it is pure configuration
    consumed by :class:`Orchestrator` or custom runners.

    Attributes:
        name: Unique agent identifier.
        description: Human-readable description of the agent's purpose.
        greeting: Jinja2 template for the agent's first-visit greeting.
        return_greeting: Jinja2 template for subsequent visits.
        handoff: Configuration declaring which tool routes TO this agent.
        model: Default LLM model configuration.
        prompt_template: Jinja2 template string for the system prompt.
        tool_names: List of tool names available to this agent.
        template_vars: Static template variables merged into prompt context.
        metadata: Arbitrary metadata for extensions.
        source_dir: Filesystem path to the agent's YAML folder (if loaded from disk).
    """

    # ── Identity ────────────────────────────────────────────────────
    name: str
    description: str = ""

    # ── Greetings (Jinja2 templates) ───────────────────────────────
    greeting: str = ""
    return_greeting: str = ""

    # ── Handoff ─────────────────────────────────────────────────────
    handoff: HandoffConfig = field(default_factory=HandoffConfig)

    # ── Model ───────────────────────────────────────────────────────
    model: ModelConfig = field(default_factory=ModelConfig)

    # ── Prompt ──────────────────────────────────────────────────────
    prompt_template: str = ""

    # ── Tools ───────────────────────────────────────────────────────
    tool_names: list[str] = field(default_factory=list)

    # ── Template variables ──────────────────────────────────────────
    template_vars: dict[str, Any] = field(default_factory=dict)

    # ── Metadata ────────────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)
    source_dir: Path | None = None

    # ── Internal caches ─────────────────────────────────────────────
    _cached_tools: list[dict[str, Any]] | None = field(
        default=None, init=False, repr=False
    )

    # ═══════════════════════════════════════════════════════════════
    # PROMPT RENDERING
    # ═══════════════════════════════════════════════════════════════

    def render_prompt(self, context: dict[str, Any] | None = None) -> str:
        """Render the system prompt template with runtime context.

        The rendering merges three layers (lowest → highest priority):

        1. **Built-in defaults** — ``agent_name`` from :attr:`name`.
        2. **Static template_vars** — from YAML ``template_vars:`` block.
        3. **Runtime context** — caller-provided overrides.

        ``None`` values in *context* are filtered out so that Jinja2's
        ``default()`` filter works correctly.

        :param context: Runtime template variables.
        :return: Rendered prompt string.
        """
        defaults: dict[str, Any] = {"agent_name": self.name}
        filtered = _filter_none(context)
        full_context = {**defaults, **self.template_vars, **filtered}

        try:
            template = Template(self.prompt_template)
            return template.render(**full_context)
        except Exception as exc:
            logger.error("prompt_render_failed", agent=self.name, error=str(exc))
            return self.prompt_template

    # ═══════════════════════════════════════════════════════════════
    # GREETING RENDERING
    # ═══════════════════════════════════════════════════════════════

    def render_greeting(self, context: dict[str, Any] | None = None) -> str | None:
        """Render the first-visit greeting template.

        :param context: Optional runtime overrides.
        :return: Rendered greeting, or ``None`` if not configured.
        """
        return self._render_template(self.greeting, context)

    def render_return_greeting(self, context: dict[str, Any] | None = None) -> str | None:
        """Render the return-visit greeting template.

        :param context: Optional runtime overrides.
        :return: Rendered return greeting, or ``None`` if not configured.
        """
        return self._render_template(self.return_greeting, context)

    def _render_template(
        self, template_str: str, context: dict[str, Any] | None = None
    ) -> str | None:
        """Render a Jinja2 template string with merged context."""
        if not template_str:
            return None
        defaults: dict[str, Any] = {"agent_name": self.name}
        filtered = _filter_none(context)
        full_context = {**defaults, **self.template_vars, **filtered}
        try:
            rendered = Template(template_str).render(**full_context)
            return rendered.strip() or None
        except Exception as exc:
            logger.error("template_render_failed", agent=self.name, error=str(exc))
            return template_str.strip() or None

    # ═══════════════════════════════════════════════════════════════
    # HANDOFF HELPERS
    # ═══════════════════════════════════════════════════════════════

    def get_handoff_tool_names(self) -> list[str]:
        """Return tool names that are handoff triggers."""
        return [t for t in self.tool_names if t.startswith("handoff_")]

    def is_handoff_target(self, tool_name: str) -> bool:
        """Check whether *tool_name* routes to this agent."""
        return self.handoff.trigger == tool_name

    # ═══════════════════════════════════════════════════════════════
    # TOOL CACHE
    # ═══════════════════════════════════════════════════════════════

    def invalidate_tool_cache(self) -> None:
        """Force the next tool schema lookup to rebuild."""
        self._cached_tools = None

    # ═══════════════════════════════════════════════════════════════
    # REPR
    # ═══════════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        return (
            f"Agent(name={self.name!r}, tools={len(self.tool_names)}, "
            f"handoff_trigger={self.handoff.trigger!r})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def build_handoff_map(agents: dict[str, Agent]) -> dict[str, str]:
    """Build a mapping of ``{tool_name: agent_name}`` from agent handoff configs.

    :param agents: Dictionary of ``agent_name → Agent``.
    :return: Dictionary of ``handoff_trigger → agent_name``.
    """
    handoff_map: dict[str, str] = {}
    for agent in agents.values():
        if agent.handoff.trigger:
            handoff_map[agent.handoff.trigger] = agent.name
    return handoff_map


def _filter_none(context: dict[str, Any] | None) -> dict[str, Any]:
    """Filter out ``None`` values so Jinja2 ``default()`` works correctly."""
    if not context:
        return {}
    return {k: v for k, v in context.items() if v is not None and v != "None"}


__all__ = [
    "Agent",
    "HandoffConfig",
    "ModelConfig",
    "build_handoff_map",
]
