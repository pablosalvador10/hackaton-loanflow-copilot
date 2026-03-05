"""foundrykit — Reusable Azure AI Foundry SDK wrapper.

Provides:
- ``FoundrySettings`` — Pydantic settings for Foundry project configuration.
- ``FoundryClient``   — Singleton wrapper around ``AgentsClient`` (v2 SDK).
- ``ToolRegistry``    — Builder for assembling ``FunctionTool`` + ``ToolSet`` with OTel tracing.
- ``AgentManager``    — Lifecycle helpers for creating, running, and cleaning up agents.
- ``create_mcp_tool`` — Factory for creating MCP tool instances.
- ``McpRunHandler``   — Auto-approval handler for MCP tool calls.
- ``build_mcp_toolset`` — Helper to build a ``ToolSet`` with MCP tools.
"""

from __future__ import annotations

from foundrykit.agent import AgentManager, AgentStreamEvent
from foundrykit.client import FoundryClient, get_foundry_client
from foundrykit.config import FoundrySettings, foundry_settings
from foundrykit.mcp import McpRunHandler, build_mcp_toolset, create_mcp_tool
from foundrykit.tools import ToolRegistry

__all__ = [
    "AgentManager",
    "AgentStreamEvent",
    "FoundryClient",
    "FoundrySettings",
    "McpRunHandler",
    "ToolRegistry",
    "build_mcp_toolset",
    "create_mcp_tool",
    "foundry_settings",
    "get_foundry_client",
]
