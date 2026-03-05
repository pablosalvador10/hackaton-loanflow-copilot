"""MCP server configuration for the Loan Origination agent.

Provides an optional MCP tool that connects the agent to external
lending-regulation or financial-data servers.  The MCP server is only
activated when ``MCP_SERVER_URL`` is set in the environment.

Usage in the loan router::

    from services.mcp_setup import get_mcp_tool, get_mcp_handler

    mcp = get_mcp_tool()
    if mcp:
        registry.add_mcp_tool(mcp)
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from foundrykit.mcp import McpRunHandler, create_mcp_tool
from opentelemetry import trace

from core.config import settings

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


@lru_cache(maxsize=1)
def get_mcp_tool():
    """Create the MCP tool if ``MCP_SERVER_URL`` is configured.

    Returns ``None`` when the MCP server URL is not set, allowing the
    application to operate in function-tools-only mode for local dev.

    :return: A configured ``McpTool`` instance, or ``None``.
    """
    if not settings.mcp_server_url:
        logger.info("mcp_disabled", reason="MCP_SERVER_URL not configured")
        return None

    with tracer.start_as_current_span("loan.create_mcp_tool") as span:
        span.set_attribute("mcp.server_url", settings.mcp_server_url)
        span.set_attribute("mcp.server_label", settings.mcp_server_label)

        try:
            headers: dict[str, str] = {}
            if settings.mcp_api_key:
                headers["Authorization"] = f"Bearer {settings.mcp_api_key}"

            allowed = (
                [t.strip() for t in settings.mcp_allowed_tools.split(",") if t.strip()]
                if settings.mcp_allowed_tools
                else []
            )

            mcp = create_mcp_tool(
                server_url=settings.mcp_server_url,
                server_label=settings.mcp_server_label,
                allowed_tools=allowed or None,
                headers=headers or None,
                approval_mode=settings.mcp_approval_mode,
            )

            logger.info(
                "mcp_tool_created",
                server_label=settings.mcp_server_label,
                server_url=settings.mcp_server_url,
                allowed_tools=allowed,
            )
            return mcp

        except Exception as e:
            logger.exception("mcp_tool_creation_failed", error=str(e))
            return None


def get_mcp_handler():
    """Create an ``McpRunHandler`` if MCP is enabled.

    :return: A ``McpRunHandler`` for auto-approval, or ``None``.
    """
    mcp = get_mcp_tool()
    if mcp is None:
        return None
    return McpRunHandler(mcp_tools=[mcp])
