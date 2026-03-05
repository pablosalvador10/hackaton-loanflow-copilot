"""Tests for the foundrykit.mcp module.

Verifies:
- ``create_mcp_tool`` factory produces correctly configured ``McpTool`` instances
- ``build_mcp_toolset`` assembles ``ToolSet`` from one or more ``McpTool`` instances
- ``McpRunHandler`` auto-approves MCP tool calls with merged headers
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from azure.ai.agents.models import McpTool, ToolSet

from foundrykit.mcp import McpRunHandler, build_mcp_toolset, create_mcp_tool


# ── create_mcp_tool ─────────────────────────────────────────────


class TestCreateMcpTool:
    """Verify ``create_mcp_tool`` factory behaviour."""

    def test_creates_tool_with_required_params(self) -> None:
        """Factory should create an McpTool with server_url and server_label."""
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="example",
        )

        assert isinstance(mcp, McpTool)
        assert mcp.server_url == "https://example.com/mcp"
        assert mcp.server_label == "example"

    def test_defaults_to_empty_allowed_tools(self) -> None:
        """When ``allowed_tools`` is not provided, it should default to an empty list."""
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
        )

        assert mcp.allowed_tools == []

    def test_sets_allowed_tools(self) -> None:
        """Allowed tools whitelist should be set on the McpTool."""
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
            allowed_tools=["tool_a", "tool_b"],
        )

        assert mcp.allowed_tools == ["tool_a", "tool_b"]

    def test_sets_custom_headers(self) -> None:
        """Custom headers should be applied via ``update_headers``."""
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
            headers={"Authorization": "Bearer secret", "X-Custom": "value"},
        )

        # Headers are stored internally by the SDK — verify via the headers property
        assert mcp.headers is not None
        assert mcp.headers.get("Authorization") == "Bearer secret"
        assert mcp.headers.get("X-Custom") == "value"

    def test_no_headers_by_default(self) -> None:
        """When no headers are provided, headers should be None or empty."""
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
        )

        # SDK may return None or empty dict depending on version
        assert not mcp.headers or len(mcp.headers) == 0

    def test_approval_mode_defaults_to_never(self) -> None:
        """The default approval mode should be 'never' (auto-approve).

        The SDK does not expose ``approval_mode`` as a readable attribute,
        so we verify the factory call completes without error.
        """
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
        )

        # Verify the tool was created successfully (approval_mode is write-only)
        assert isinstance(mcp, McpTool)

    def test_approval_mode_always(self) -> None:
        """Setting approval_mode to 'always' should not raise.

        The SDK does not expose ``approval_mode`` as a readable attribute,
        so we verify the factory call completes without error.
        """
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
            approval_mode="always",
        )

        assert isinstance(mcp, McpTool)


# ── build_mcp_toolset ───────────────────────────────────────────


class TestBuildMcpToolset:
    """Verify ``build_mcp_toolset`` assembles ToolSet correctly."""

    def test_builds_toolset_with_single_mcp(self) -> None:
        """A single McpTool should produce a valid ToolSet."""
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="single",
        )

        toolset = build_mcp_toolset(mcp)

        assert isinstance(toolset, ToolSet)

    def test_builds_toolset_with_multiple_mcps(self) -> None:
        """Multiple McpTools should all be added to the same ToolSet."""
        mcp1 = create_mcp_tool(
            server_url="https://server-a.com/mcp",
            server_label="server-a",
        )
        mcp2 = create_mcp_tool(
            server_url="https://server-b.com/mcp",
            server_label="server-b",
        )

        toolset = build_mcp_toolset(mcp1, mcp2)

        assert isinstance(toolset, ToolSet)

    def test_extends_existing_toolset(self) -> None:
        """When ``existing_toolset`` is provided, it should be reused."""
        existing = ToolSet()
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="extend",
        )

        toolset = build_mcp_toolset(mcp, existing_toolset=existing)

        # Should be the exact same ToolSet object
        assert toolset is existing

    def test_raises_when_no_tools_provided(self) -> None:
        """Should raise ValueError when called with no McpTool arguments."""
        with pytest.raises(ValueError, match="At least one McpTool"):
            build_mcp_toolset()


# ── McpRunHandler ───────────────────────────────────────────────


class TestMcpRunHandler:
    """Verify ``McpRunHandler`` auto-approval behaviour."""

    def test_auto_approve_defaults_to_true(self) -> None:
        """Handler should auto-approve by default."""
        handler = McpRunHandler()

        assert handler._auto_approve is True

    def test_auto_approve_can_be_disabled(self) -> None:
        """Handler should support disabling auto-approval."""
        handler = McpRunHandler(auto_approve=False)

        assert handler._auto_approve is False

    def test_merges_headers_from_mcp_tools(self) -> None:
        """Handler should merge headers from all provided McpTool instances."""
        mcp1 = create_mcp_tool(
            server_url="https://a.com/mcp",
            server_label="a",
            headers={"Authorization": "Bearer token-a"},
        )
        mcp2 = create_mcp_tool(
            server_url="https://b.com/mcp",
            server_label="b",
            headers={"X-Api-Key": "key-b"},
        )

        handler = McpRunHandler(mcp_tools=[mcp1, mcp2])

        assert handler._merged_headers.get("Authorization") == "Bearer token-a"
        assert handler._merged_headers.get("X-Api-Key") == "key-b"

    def test_submit_mcp_tool_approval_approves(self) -> None:
        """``submit_mcp_tool_approval`` should return an approved ToolApproval."""
        handler = McpRunHandler()

        mock_run = MagicMock()
        mock_tool_call = MagicMock()
        mock_tool_call.id = "tc-001"

        approval = handler.submit_mcp_tool_approval(
            run=mock_run,
            tool_call=mock_tool_call,
        )

        assert approval.approve is True
        assert approval.tool_call_id == "tc-001"

    def test_submit_mcp_tool_approval_rejects_when_disabled(self) -> None:
        """When ``auto_approve=False``, approval.approve should be False."""
        handler = McpRunHandler(auto_approve=False)

        mock_run = MagicMock()
        mock_tool_call = MagicMock()
        mock_tool_call.id = "tc-002"

        approval = handler.submit_mcp_tool_approval(
            run=mock_run,
            tool_call=mock_tool_call,
        )

        assert approval.approve is False
        assert approval.tool_call_id == "tc-002"

    def test_submit_mcp_tool_approval_includes_headers(self) -> None:
        """Approval should include merged headers from MCP tools."""
        mcp = create_mcp_tool(
            server_url="https://a.com/mcp",
            server_label="a",
            headers={"Authorization": "Bearer secret"},
        )

        handler = McpRunHandler(mcp_tools=[mcp])

        mock_run = MagicMock()
        mock_tool_call = MagicMock()
        mock_tool_call.id = "tc-003"

        approval = handler.submit_mcp_tool_approval(
            run=mock_run,
            tool_call=mock_tool_call,
        )

        assert approval.headers is not None
        assert approval.headers.get("Authorization") == "Bearer secret"

    def test_empty_mcp_tools_no_headers(self) -> None:
        """Handler with no MCP tools should have empty merged headers."""
        handler = McpRunHandler()

        assert handler._merged_headers == {}

