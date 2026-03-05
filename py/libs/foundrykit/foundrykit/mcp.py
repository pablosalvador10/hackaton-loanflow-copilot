"""MCP (Model Context Protocol) tool helpers for Azure AI Agent Service.

Provides convenience wrappers around the ``McpTool`` class from the
``azure-ai-agents`` SDK (≥1.2.0b3) for integrating remote MCP servers
with Foundry agents.

MCP tools are **server-side** — the Azure Agent Service calls the remote
MCP server directly.  Unlike local ``FunctionTool`` functions, there is
no client-side code to execute.  The only client-side concern is
**tool-call approval** (human-in-the-loop), which can be automated or
disabled.

Usage::

    from foundrykit.mcp import create_mcp_tool, McpRunHandler

    mcp = create_mcp_tool(
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        server_label="github",
    )

    # Add to a ToolSet alongside local functions
    from azure.ai.agents.models import ToolSet
    toolset = ToolSet()
    toolset.add(mcp)

    # Use auto-approval handler for create_and_process
    handler = McpRunHandler(mcp_tools=[mcp])
"""

from __future__ import annotations

from typing import Any

import structlog
from azure.ai.agents.models import (
    McpTool,
    RequiredMcpToolCall,
    RunHandler,
    SubmitToolApprovalAction,
    ThreadRun,
    ToolApproval,
    ToolSet,
)
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("foundrykit.mcp")


# ── Factory Helper ──────────────────────────────────────────────


def create_mcp_tool(
    *,
    server_url: str,
    server_label: str,
    allowed_tools: list[str] | None = None,
    headers: dict[str, str] | None = None,
    approval_mode: str = "never",
) -> McpTool:
    """Create and configure an ``McpTool`` instance.

    :param server_url: The URL of the remote MCP server (Streamable HTTP).
    :param server_label: A human-readable label for the MCP server.
    :param allowed_tools: Optional whitelist of tool names the agent may call.
        Pass an empty list (default) to allow all tools exposed by the server.
    :param headers: Optional dict of custom headers to send to the MCP server
        (e.g. auth tokens).  Keys and values are strings.
    :param approval_mode: ``"never"`` (auto-approve, default) or ``"always"``
        (require explicit approval per tool call).
    :return: Configured ``McpTool`` ready to add to a ``ToolSet``.
    """
    with tracer.start_as_current_span("foundrykit.create_mcp_tool") as span:
        span.set_attribute("mcp.server_url", server_url)
        span.set_attribute("mcp.server_label", server_label)

        mcp = McpTool(
            server_label=server_label,
            server_url=server_url,
            allowed_tools=allowed_tools or [],
        )

        # Apply custom headers (e.g. API keys)
        if headers:
            for key, value in headers.items():
                mcp.update_headers(key, value)
            logger.debug("mcp_headers_set", count=len(headers))

        # Set approval mode
        mcp.set_approval_mode(approval_mode)
        logger.info(
            "mcp_tool_created",
            server_label=server_label,
            server_url=server_url,
            approval_mode=approval_mode,
            allowed_tools=allowed_tools or [],
        )
        return mcp


def build_mcp_toolset(
    *mcp_tools: McpTool,
    existing_toolset: ToolSet | None = None,
) -> ToolSet:
    """Build a ``ToolSet`` containing one or more ``McpTool`` instances.

    :param mcp_tools: One or more ``McpTool`` objects to include.
    :param existing_toolset: Optional existing ``ToolSet`` to extend (e.g. one
        that already contains ``FunctionTool`` definitions).
    :return: A ``ToolSet`` ready to pass to ``create_agent()``.
    :raises ValueError: If no MCP tools are provided.
    """
    if not mcp_tools:
        raise ValueError("At least one McpTool must be provided.")

    toolset = existing_toolset or ToolSet()
    for mcp in mcp_tools:
        toolset.add(mcp)

    logger.info(
        "mcp_toolset_built",
        mcp_count=len(mcp_tools),
        labels=[m.server_label for m in mcp_tools],
    )
    return toolset


# ── RunHandler for create_and_process ───────────────────────────


class McpRunHandler(RunHandler):
    """Auto-approval handler for MCP tool calls during ``create_and_process``.

    When the agent invokes an MCP tool, the SDK pauses and asks the client
    to approve or reject the call.  This handler **auto-approves** all
    MCP tool calls and attaches the configured headers.

    :param mcp_tools: List of ``McpTool`` instances whose headers should
        be forwarded during approval.
    :param auto_approve: Whether to approve all MCP calls automatically.
        Defaults to ``True``.

    Usage::

        handler = McpRunHandler(mcp_tools=[mcp_tool])
        run = agents_client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id,
            run_handler=handler,
        )
    """

    def __init__(
        self,
        mcp_tools: list[McpTool] | None = None,
        *,
        auto_approve: bool = True,
    ) -> None:
        self._mcp_tools = mcp_tools or []
        self._auto_approve = auto_approve
        # Merge all headers from all MCP tools
        self._merged_headers: dict[str, str] = {}
        for mcp in self._mcp_tools:
            if hasattr(mcp, "headers") and mcp.headers:
                self._merged_headers.update(mcp.headers)

    def submit_mcp_tool_approval(
        self,
        *,
        run: ThreadRun,
        tool_call: RequiredMcpToolCall,
        **kwargs: Any,
    ) -> ToolApproval:
        """Handle MCP tool approval requests.

        :param run: The current thread run.
        :param tool_call: The MCP tool call requiring approval.
        :return: A ``ToolApproval`` with the approval decision and headers.
        """
        with tracer.start_as_current_span("foundrykit.mcp_tool_approval") as span:
            span.set_attribute("tool_call.id", tool_call.id)
            span.set_attribute("approved", self._auto_approve)

            logger.info(
                "mcp_tool_approval",
                tool_call_id=tool_call.id,
                approved=self._auto_approve,
            )

            return ToolApproval(
                tool_call_id=tool_call.id,
                approve=self._auto_approve,
                headers=self._merged_headers or None,
            )
