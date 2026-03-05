"""Tests for ToolRegistry MCP integration and the _StreamCollector MCP approval flow.

Verifies:
- ``ToolRegistry.add_mcp_tool()`` registers remote McpTool instances
- ``ToolRegistry.build_toolset()`` builds a combined ToolSet (functions + MCP)
- ``ToolRegistry.build_toolset()`` works with MCP-only (no local functions)
- ``_StreamCollector`` auto-approves MCP tool calls during streaming
- ``run_agent()`` forwards ``run_handler`` to ``create_and_process``
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from azure.ai.agents.models import (
    McpTool,
    RequiredMcpToolCall,
    SubmitToolApprovalAction,
    ToolApproval,
    ToolSet,
)

from foundrykit.agent import AgentManager, AgentStreamEvent, _StreamCollector
from foundrykit.mcp import McpRunHandler, create_mcp_tool
from foundrykit.tools import ToolRegistry


# ── Helpers ─────────────────────────────────────────────────────


def _make_mock_client(model: str = "gpt-4-1") -> MagicMock:
    """Build a mock ``FoundryClient`` with v2 agents_client surface."""
    client = MagicMock()
    client.model_deployment = model
    agents = MagicMock()
    client.agents_client = agents
    return client


def _make_mock_agent(agent_id: str = "agent-001") -> MagicMock:
    agent = MagicMock()
    agent.id = agent_id
    return agent


def _make_mock_thread(thread_id: str = "thread-001") -> MagicMock:
    thread = MagicMock()
    thread.id = thread_id
    return thread


def _make_successful_run() -> MagicMock:
    run = MagicMock()
    run.status = "completed"
    run.last_error = None
    return run


# ── ToolRegistry MCP integration ────────────────────────────────


class TestToolRegistryMcp:
    """Verify ``ToolRegistry`` MCP tool support."""

    def test_add_mcp_tool_stores_tool(self) -> None:
        """``add_mcp_tool`` should store the McpTool in the registry."""
        registry = ToolRegistry()
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
        )

        registry.add_mcp_tool(mcp)

        assert len(registry._mcp_tools) == 1
        assert registry._mcp_tools[0] is mcp

    def test_add_multiple_mcp_tools(self) -> None:
        """Multiple MCP tools can be added to the same registry."""
        registry = ToolRegistry()
        mcp1 = create_mcp_tool(
            server_url="https://a.com/mcp",
            server_label="a",
        )
        mcp2 = create_mcp_tool(
            server_url="https://b.com/mcp",
            server_label="b",
        )

        registry.add_mcp_tool(mcp1)
        registry.add_mcp_tool(mcp2)

        assert len(registry._mcp_tools) == 2

    def test_build_toolset_mcp_only(self) -> None:
        """Building a toolset with only MCP tools (no functions) should work."""
        registry = ToolRegistry()
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
        )
        registry.add_mcp_tool(mcp)

        toolset = registry.build_toolset()

        assert isinstance(toolset, ToolSet)

    def test_build_toolset_mixed_functions_and_mcp(self) -> None:
        """Building a toolset with both functions and MCP tools should work."""
        registry = ToolRegistry()

        @registry.register
        def local_tool(x: str) -> str:
            """A local tool."""
            return x

        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
        )
        registry.add_mcp_tool(mcp)

        toolset = registry.build_toolset()

        assert isinstance(toolset, ToolSet)
        assert len(registry.function_list) == 1
        assert len(registry._mcp_tools) == 1

    def test_build_toolset_raises_when_empty(self) -> None:
        """Should raise RuntimeError when neither functions nor MCP tools are registered."""
        registry = ToolRegistry()

        with pytest.raises(RuntimeError, match="No tools registered"):
            registry.build_toolset()


# ── AgentManager.run_agent with run_handler ─────────────────────


class TestRunAgentWithMcpHandler:
    """Verify ``run_agent()`` passes ``run_handler`` to ``create_and_process``."""

    def test_run_handler_forwarded(self) -> None:
        """When ``run_handler`` is provided, it should be passed to create_and_process."""
        mock_client = _make_mock_client()
        mock_thread = _make_mock_thread()
        mock_client.agents_client.threads.create.return_value = mock_thread
        mock_client.agents_client.runs.create_and_process.return_value = _make_successful_run()
        mock_client.agents_client.messages.get_last_message_text_by_role.return_value = "Done"

        handler = McpRunHandler()
        manager = AgentManager(mock_client)
        result = manager.run_agent(
            "agent-001",
            "test message",
            run_handler=handler,
        )

        mock_client.agents_client.runs.create_and_process.assert_called_once_with(
            thread_id="thread-001",
            agent_id="agent-001",
            run_handler=handler,
        )
        assert result == "Done"

    def test_no_run_handler_omits_kwarg(self) -> None:
        """When no ``run_handler`` is provided, it should not appear in kwargs."""
        mock_client = _make_mock_client()
        mock_thread = _make_mock_thread()
        mock_client.agents_client.threads.create.return_value = mock_thread
        mock_client.agents_client.runs.create_and_process.return_value = _make_successful_run()
        mock_client.agents_client.messages.get_last_message_text_by_role.return_value = "Hi"

        manager = AgentManager(mock_client)
        manager.run_agent("agent-001", "test")

        mock_client.agents_client.runs.create_and_process.assert_called_once_with(
            thread_id="thread-001",
            agent_id="agent-001",
        )


# ── _StreamCollector MCP approval ──────────────────────────────


class TestStreamCollectorMcpApproval:
    """Verify ``_StreamCollector.on_thread_run`` handles MCP approvals."""

    def _make_mcp_run(
        self,
        thread_id: str = "thread-001",
        run_id: str = "run-001",
        tool_call_ids: list[str] | None = None,
    ) -> MagicMock:
        """Build a mock ThreadRun with SubmitToolApprovalAction."""
        tool_call_ids = tool_call_ids or ["tc-001"]

        mock_run = MagicMock()
        mock_run.status = "requires_action"
        mock_run.thread_id = thread_id
        mock_run.id = run_id

        # Build RequiredMcpToolCall mocks
        tool_calls = []
        for tc_id in tool_call_ids:
            tc = MagicMock(spec=RequiredMcpToolCall)
            tc.id = tc_id
            tool_calls.append(tc)

        # Build SubmitToolApprovalAction
        approval_action = MagicMock(spec=SubmitToolApprovalAction)
        approval_action.submit_tool_approval.tool_calls = tool_calls

        mock_run.required_action = approval_action
        return mock_run

    def test_auto_approves_mcp_tool_calls(self) -> None:
        """Collector should auto-approve MCP tool calls and emit mcp_approved events."""
        mcp = create_mcp_tool(
            server_url="https://example.com/mcp",
            server_label="test",
        )

        mock_agents_client = MagicMock()
        collector = _StreamCollector(
            agents_client=mock_agents_client,
            mcp_tools=[mcp],
        )

        mock_run = self._make_mcp_run(tool_call_ids=["tc-001", "tc-002"])
        collector.on_thread_run(mock_run)

        # Should have emitted mcp_approved events
        approved_events = [e for e in collector.events if e.event_type == "mcp_approved"]
        assert len(approved_events) == 2

        # Should have submitted tool approvals
        mock_agents_client.runs.submit_tool_outputs_stream.assert_called_once()
        call_kwargs = mock_agents_client.runs.submit_tool_outputs_stream.call_args
        assert call_kwargs[1]["thread_id"] == "thread-001"
        assert call_kwargs[1]["run_id"] == "run-001"
        assert len(call_kwargs[1]["tool_approvals"]) == 2

    def test_no_approval_without_mcp_tools(self) -> None:
        """Without MCP tools, approval action should not trigger approval logic."""
        mock_agents_client = MagicMock()
        collector = _StreamCollector(
            agents_client=mock_agents_client,
            mcp_tools=[],
        )

        # Simulate a SubmitToolApprovalAction — should NOT trigger approval
        mock_run = self._make_mcp_run()
        # Clear the required_action type check by not having mcp_tools
        collector.on_thread_run(mock_run)

        # submit_tool_outputs_stream should NOT have been called
        mock_agents_client.runs.submit_tool_outputs_stream.assert_not_called()

    def test_merges_headers_from_multiple_mcp_tools(self) -> None:
        """Headers from multiple MCP tools should be merged in the collector."""
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

        collector = _StreamCollector(
            agents_client=MagicMock(),
            mcp_tools=[mcp1, mcp2],
        )

        assert collector._mcp_headers.get("Authorization") == "Bearer token-a"
        assert collector._mcp_headers.get("X-Api-Key") == "key-b"

    def test_handles_completed_run(self) -> None:
        """Completed run should emit run_completed event."""
        collector = _StreamCollector()

        mock_run = MagicMock()
        mock_run.status = "completed"
        mock_run.required_action = None

        collector.on_thread_run(mock_run)

        assert any(e.event_type == "run_completed" for e in collector.events)

    def test_handles_failed_run(self) -> None:
        """Failed run should emit error event."""
        collector = _StreamCollector()

        mock_run = MagicMock()
        mock_run.status = "failed"
        mock_run.required_action = None
        mock_run.last_error = "Something broke"

        collector.on_thread_run(mock_run)

        error_events = [e for e in collector.events if e.event_type == "error"]
        assert len(error_events) == 1
        assert "Something broke" in error_events[0].data

