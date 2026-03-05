"""Tool registry for building ``FunctionTool`` + ``ToolSet`` with automatic OTel tracing.

Usage::

    from foundrykit import ToolRegistry

    registry = ToolRegistry()

    @registry.register
    def decode_vin(vin: str) -> str:
        \"\"\"Decode a Vehicle Identification Number via the NHTSA API.\"\"\"
        ...

    toolset = registry.build_toolset()
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import Any

import structlog
from azure.ai.agents.models import FunctionTool, McpTool, ToolSet
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("foundrykit.tools")


class ToolRegistry:
    """Collects Python functions and wraps them as Foundry ``FunctionTool`` definitions.

    Each registered function is automatically instrumented with an OTel span
    and structured logging.

    Optionally, ``McpTool`` instances can be added so that both local
    function tools and remote MCP tools live in the same ``ToolSet``.
    """

    def __init__(self) -> None:
        self._functions: list[Callable[..., Any]] = []
        self._mcp_tools: list[McpTool] = []

    def register(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator that registers a function as an agent tool.

        The original function is wrapped with OTel tracing and structlog
        logging.  The wrapper preserves the function's name, docstring,
        and type hints so that ``FunctionTool`` can auto-generate the
        JSON Schema correctly.

        :param fn: The tool function to register.
        :return: The wrapped function (same signature).
        """
        tool_name = fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(f"tool.{tool_name}") as span:
                span.set_attribute("tool.name", tool_name)
                span.set_attribute("tool.args", _safe_json(kwargs or args))

                logger.info("tool_call_start", tool=tool_name)
                try:
                    result = fn(*args, **kwargs)
                    span.set_attribute("tool.result", _safe_json(result)[:2000])
                    logger.info("tool_call_success", tool=tool_name)
                    return result
                except Exception as e:
                    span.set_attribute("tool.error", str(e))
                    logger.exception("tool_call_failed", tool=tool_name, error=str(e))
                    raise

        self._functions.append(wrapper)
        logger.debug("tool_registered", tool=tool_name)
        return wrapper

    def add_mcp_tool(self, mcp: McpTool) -> None:
        """Add a remote ``McpTool`` to this registry.

        MCP tools are server-side — the Azure Agent Service calls the
        remote MCP server.  They require no local function execution.

        :param mcp: A configured ``McpTool`` instance.
        """
        self._mcp_tools.append(mcp)
        logger.debug("mcp_tool_added", label=mcp.server_label)

    def build_toolset(self) -> ToolSet:
        """Build a Foundry ``ToolSet`` from all registered functions and MCP tools.

        :return: A ``ToolSet`` ready to pass to ``create_agent()``.
        :raises RuntimeError: If no functions or MCP tools have been registered.
        """
        if not self._functions and not self._mcp_tools:
            raise RuntimeError(
                "No tools registered.  Use @registry.register or "
                "registry.add_mcp_tool() first."
            )

        toolset = ToolSet()

        if self._functions:
            functions = FunctionTool(self._functions)
            toolset.add(functions)

        for mcp in self._mcp_tools:
            toolset.add(mcp)

        logger.info(
            "toolset_built",
            function_count=len(self._functions),
            mcp_count=len(self._mcp_tools),
            functions=[fn.__name__ for fn in self._functions],
            mcp_labels=[m.server_label for m in self._mcp_tools],
        )
        return toolset

    @property
    def function_list(self) -> list[Callable[..., Any]]:
        """Return the list of registered (wrapped) functions.

        :return: List of callable tool functions.
        """
        return list(self._functions)


def _safe_json(obj: Any) -> str:
    """Serialise *obj* to JSON for span attributes, with a fallback to ``str()``.

    :param obj: Object to serialise.
    :return: JSON string representation.
    """
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return str(obj)
