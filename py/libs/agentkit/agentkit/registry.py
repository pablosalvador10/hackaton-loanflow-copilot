"""Global tool registry — singleton pattern with import-time registration.

The tool registry is the central store for all tool definitions.  Each tool
has a schema (OpenAI function-calling format), an executor (sync or async
callable), and metadata (handoff flag, tags).

Tools register at module-import time via :func:`register_tool`, and the
registry is initialised by calling :func:`ToolRegistry.initialize` which
imports all tool modules.

Design pattern (from ART Voice Agent):

1. Each tool module calls ``registry.tool()`` at import time.
2. ``registry.initialize()`` triggers imports (side-effect registration).
3. Agents reference tools by name; the orchestrator resolves via registry.

Usage::

    from agentkit import ToolRegistry

    registry = ToolRegistry()

    @registry.tool(tags={"banking"})
    async def get_balance(account_id: str) -> dict:
        \"\"\"Get account balance.\"\"\"
        return {"account_id": account_id, "balance": 1000.0}

    # Or register with explicit schema
    registry.register(
        name="get_balance",
        schema={...},
        executor=get_balance_fn,
        is_handoff=False,
    )

    # Build OpenAI tool list for an agent
    tools = registry.get_tools_for_agent(["get_balance"])

    # Execute a tool
    result = await registry.execute("get_balance", {"account_id": "123"})
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import typing
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeAlias

import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("agentkit.tools")

# Type aliases
ToolExecutor: TypeAlias = Callable[..., Any]
AsyncToolExecutor: TypeAlias = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ToolDefinition:
    """Complete tool definition with schema and executor.

    :param name: Unique tool name.
    :param schema: OpenAI function-calling schema (``{"name": ..., "description": ..., "parameters": ...}``).
    :param executor: The callable that implements the tool (sync or async).
    :param is_handoff: ``True`` if this tool triggers an agent handoff.
    :param description: Human-readable description.
    :param tags: Categorisation tags (e.g. ``{"banking", "auth"}``).
    """

    name: str
    schema: dict[str, Any]
    executor: ToolExecutor
    is_handoff: bool = False
    description: str = ""
    tags: set[str] = field(default_factory=set)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class ToolRegistry:
    """Central registry for all agent tools.

    Supports two registration styles:

    1. **Decorator** — ``@registry.tool()`` for auto-schema generation from
       docstrings and type hints.
    2. **Imperative** — ``registry.register(name, schema, executor)`` for
       explicit schema control.

    The registry also handles tool execution with automatic sync/async
    detection and OpenTelemetry tracing.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._initialized: bool = False

    # ── Decorator registration ──────────────────────────────────────

    def tool(
        self,
        *,
        name: str | None = None,
        is_handoff: bool = False,
        tags: set[str] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that registers a function as an agent tool.

        Automatically generates an OpenAI-compatible function schema from the
        function's name, docstring, and type hints.

        The wrapper adds OTel tracing and structlog logging.

        :param name: Override tool name (defaults to ``fn.__name__``).
        :param is_handoff: Mark as a handoff tool.
        :param tags: Optional categorisation tags.
        :return: Decorator function.

        Example::

            @registry.tool(tags={"banking"})
            async def get_balance(account_id: str) -> dict:
                \"\"\"Get the current balance for an account.

                :param account_id: The account identifier.
                \"\"\"
                return {"balance": 1000.0}
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or fn.__name__

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracer.start_as_current_span(f"tool.{tool_name}") as span:
                    span.set_attribute("tool.name", tool_name)
                    span.set_attribute("tool.args", _safe_json(kwargs or args))
                    logger.info("tool_call_start", tool=tool_name)
                    try:
                        if inspect.iscoroutinefunction(fn):
                            result = await fn(*args, **kwargs)
                        else:
                            result = await asyncio.to_thread(fn, *args, **kwargs)
                        span.set_attribute(
                            "tool.result", _safe_json(result)[:2000]
                        )
                        logger.info("tool_call_success", tool=tool_name)
                        return result
                    except Exception as exc:
                        span.set_attribute("tool.error", str(exc))
                        logger.exception(
                            "tool_call_failed", tool=tool_name, error=str(exc)
                        )
                        raise

            # Generate schema from function signature
            schema = _build_schema_from_function(fn, tool_name)

            self._definitions[tool_name] = ToolDefinition(
                name=tool_name,
                schema=schema,
                executor=async_wrapper,
                is_handoff=is_handoff,
                description=schema.get("description", ""),
                tags=tags or set(),
            )
            logger.debug("tool_registered", tool=tool_name, is_handoff=is_handoff)
            return async_wrapper

        return decorator

    # ── Imperative registration ─────────────────────────────────────

    def register(
        self,
        name: str,
        schema: dict[str, Any],
        executor: ToolExecutor,
        *,
        is_handoff: bool = False,
        tags: set[str] | None = None,
        override: bool = False,
    ) -> None:
        """Register a tool with an explicit schema and executor.

        :param name: Unique tool name.
        :param schema: OpenAI function-calling schema.
        :param executor: Callable implementation (sync or async).
        :param is_handoff: ``True`` if this tool triggers agent handoff.
        :param tags: Optional categorisation tags.
        :param override: If ``True``, replace existing registration.
        """
        if name in self._definitions and not override:
            logger.debug("tool_already_registered", tool=name)
            return

        self._definitions[name] = ToolDefinition(
            name=name,
            schema=schema,
            executor=executor,
            is_handoff=is_handoff,
            description=schema.get("description", ""),
            tags=tags or set(),
        )
        logger.debug("tool_registered", tool=name, is_handoff=is_handoff)

    # ── Handoff tool helper ─────────────────────────────────────────

    def register_handoff(
        self,
        name: str,
        *,
        target_agent: str,
        description: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Register a handoff tool with a standard schema.

        Creates a schema and executor that returns a handoff result dict.

        :param name: Tool name (e.g. ``"handoff_fraud_agent"``).
        :param target_agent: Agent name to hand off to.
        :param description: Tool description.
        :param parameters: Optional custom parameters schema.
        """
        schema = {
            "name": name,
            "description": description or f"Transfer the conversation to {target_agent}.",
            "parameters": parameters or {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for the handoff.",
                    },
                    "context": {
                        "type": "object",
                        "description": "Context to pass to the target agent.",
                    },
                },
            },
        }

        async def executor(reason: str = "", context: dict | None = None, **kwargs: Any) -> dict:
            return {
                "handoff": True,
                "target_agent": target_agent,
                "message": f"Connecting you to {target_agent}.",
                "handoff_summary": reason,
                "handoff_context": context or {},
            }

        self.register(name, schema, executor, is_handoff=True)

    # ── Generic handoff tool ────────────────────────────────────────

    def register_generic_handoff(self) -> None:
        """Register the generic ``handoff_to_agent`` tool.

        This enables dynamic routing without pre-registered tool names.
        The model specifies ``target_agent`` at call time.
        """
        schema = {
            "name": "handoff_to_agent",
            "description": (
                "Transfer the conversation to a different specialist agent. "
                "Use this when the user's request falls outside your expertise."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target_agent": {
                        "type": "string",
                        "description": "Name of the agent to hand off to.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the handoff.",
                    },
                    "context": {
                        "type": "object",
                        "description": "Context to pass to the target agent.",
                    },
                },
                "required": ["target_agent"],
            },
        }

        async def executor(
            target_agent: str, reason: str = "", context: dict | None = None, **kwargs: Any
        ) -> dict:
            return {
                "handoff": True,
                "target_agent": target_agent,
                "message": f"Connecting you to {target_agent}.",
                "handoff_summary": reason,
                "handoff_context": context or {},
            }

        self.register("handoff_to_agent", schema, executor, is_handoff=True)

    # ── Query methods ───────────────────────────────────────────────

    def get_tools_for_agent(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Build an OpenAI-compatible tool list for the specified tools.

        :param tool_names: Tool names to include.
        :return: List of ``{"type": "function", "function": schema}`` dicts.
        """
        tools: list[dict[str, Any]] = []
        for name in tool_names:
            defn = self._definitions.get(name)
            if defn:
                tools.append({"type": "function", "function": defn.schema})
            else:
                logger.warning("tool_not_found", tool=name)
        return tools

    def get_definition(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._definitions.get(name)

    def is_handoff_tool(self, name: str) -> bool:
        """Check whether a tool triggers an agent handoff."""
        defn = self._definitions.get(name)
        return defn.is_handoff if defn else False

    def list_tools(
        self, *, tags: set[str] | None = None, handoffs_only: bool = False
    ) -> list[str]:
        """List registered tool names with optional filtering.

        :param tags: Only return tools with ALL specified tags.
        :param handoffs_only: Only return handoff tools.
        """
        result: list[str] = []
        for name, defn in self._definitions.items():
            if handoffs_only and not defn.is_handoff:
                continue
            if tags and not tags.issubset(defn.tags):
                continue
            result.append(name)
        return result

    # ── Execution ───────────────────────────────────────────────────

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a registered tool by name.

        Handles both sync and async executors.  Sync executors are run in
        a thread pool via ``asyncio.to_thread()``.

        :param name: Tool name.
        :param arguments: Tool arguments (dict).
        :return: Tool result dict.
        """
        defn = self._definitions.get(name)
        if not defn:
            return {
                "success": False,
                "error": f"Tool '{name}' not found",
                "message": f"Tool '{name}' is not registered.",
            }

        fn = defn.executor
        try:
            if inspect.iscoroutinefunction(fn):
                result = await fn(**arguments)
            else:
                result = await asyncio.to_thread(fn, **arguments)

            if isinstance(result, dict):
                return result
            return {"success": True, "result": result}

        except Exception as exc:
            logger.exception("tool_execution_failed", tool=name)
            return {
                "success": False,
                "error": str(exc),
                "message": f"Tool execution failed: {exc}",
            }

    # ── Reset (for testing) ─────────────────────────────────────────

    def reset(self) -> None:
        """Clear all registered tools (primarily for testing)."""
        self._definitions.clear()
        self._initialized = False

    @property
    def tool_count(self) -> int:
        """Number of registered tools."""
        return len(self._definitions)

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={self.tool_count})"


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

# Mapping from Python types to JSON Schema types
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _build_schema_from_function(fn: Callable[..., Any], name: str) -> dict[str, Any]:
    """Generate an OpenAI function-calling schema from a function's signature.

    Extracts parameter types from type hints and descriptions from the
    docstring (using ``:param name: description`` format).

    :param fn: The tool function.
    :param name: Tool name.
    :return: OpenAI function schema dict.
    """
    sig = inspect.signature(fn)
    doc = inspect.getdoc(fn) or ""

    # Resolve type hints (handles `from __future__ import annotations`)
    try:
        type_hints = typing.get_type_hints(fn)
    except Exception:
        type_hints = {}

    # Extract parameter descriptions from docstring
    param_docs = _parse_param_docs(doc)

    # Extract the main description (lines before :param/:return/:raises)
    description_lines: list[str] = []
    for line in doc.split("\n"):
        stripped = line.strip()
        if stripped.startswith((":param", ":return", ":raises", "Args:", "Returns:", "Raises:")):
            break
        description_lines.append(stripped)
    description = " ".join(description_lines).strip()

    # Build parameters schema
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls", "kwargs", "args"):
            continue

        # Prefer resolved type hints over raw annotation
        annotation = type_hints.get(param_name, param.annotation)
        json_type = "string"  # default

        if annotation is not inspect.Parameter.empty:
            # Handle Optional, Union, etc.
            origin = getattr(annotation, "__origin__", None)
            if origin is not None:
                # e.g., list[str], dict[str, Any]
                json_type = _TYPE_MAP.get(origin, "string")
            else:
                json_type = _TYPE_MAP.get(annotation, "string")

        prop: dict[str, Any] = {"type": json_type}
        if param_name in param_docs:
            prop["description"] = param_docs[param_name]

        properties[param_name] = prop

        # Required if no default value
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    schema: dict[str, Any] = {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
        },
    }

    if required:
        schema["parameters"]["required"] = required

    return schema


def _parse_param_docs(docstring: str) -> dict[str, str]:
    """Extract ``:param name: description`` pairs from a docstring.

    Also handles Google-style ``Args:`` blocks.

    :param docstring: The function's docstring.
    :return: Dict of ``{param_name: description}``.
    """
    params: dict[str, str] = {}
    if not docstring:
        return params

    # Sphinx-style :param name: description
    import re

    for match in re.finditer(r":param\s+(\w+):\s*(.+?)(?=\n\s*:|$)", docstring, re.DOTALL):
        params[match.group(1)] = match.group(2).strip()

    # Google-style Args: block
    if not params:
        in_args = False
        for line in docstring.split("\n"):
            stripped = line.strip()
            if stripped == "Args:":
                in_args = True
                continue
            if in_args:
                if stripped and not stripped.startswith(("Returns:", "Raises:", "Example")):
                    # "param_name: description" or "param_name (type): description"
                    m = re.match(r"(\w+)(?:\s*\([^)]*\))?\s*:\s*(.+)", stripped)
                    if m:
                        params[m.group(1)] = m.group(2).strip()
                else:
                    in_args = False

    return params


def _safe_json(obj: Any) -> str:
    """Serialise to JSON for span attributes, with ``str()`` fallback."""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return str(obj)


__all__ = [
    "ToolDefinition",
    "ToolRegistry",
]
