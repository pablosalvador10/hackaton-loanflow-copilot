"""Tests for AgentManager v2 SDK integration.

Verifies that foundrykit uses the ``AgentsClient`` (v2) API surface correctly:
- flat ``create_agent`` / ``delete_agent`` on the client
- ``enable_auto_function_calls`` instead of manual FunctionTool registration
- ``messages.get_last_message_text_by_role`` for response extraction
- ``runs.create_and_process`` via the ``_agents`` property
- ``threads.create`` / ``messages.create`` sub-operations
- ``temporary_agent`` context-manager lifecycle
- retry-after handling for 429 errors
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from azure.ai.agents.models import MessageRole, ToolSet
from azure.core.exceptions import HttpResponseError

from foundrykit.agent import AgentManager, AgentStreamEvent


# ── Helpers ─────────────────────────────────────────────────────


def _make_mock_client(model: str = "gpt-4-1") -> MagicMock:
    """Build a mock ``FoundryClient`` whose ``agents_client`` behaves like v2."""
    client = MagicMock()
    client.model_deployment = model

    # The agents_client mock auto-generates sub-attrs (.threads, .messages, .runs)
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


def _make_failed_run(error: str = "Something went wrong") -> MagicMock:
    run = MagicMock()
    run.status = "failed"
    run.last_error = error
    return run


# ── Test: create_agent calls AgentsClient.create_agent (flat) ───


class TestCreateAgentV2:
    """Verify create_agent uses the v2 flat ``create_agent`` method."""

    def test_calls_flat_create_agent(self):
        """create_agent must call ``agents_client.create_agent()`` — not
        ``agents_client.agents.create_agent()`` (v1 pattern)."""
        mock_client = _make_mock_client()
        mock_agent = _make_mock_agent()
        mock_client.agents_client.create_agent.return_value = mock_agent

        manager = AgentManager(mock_client)
        result = manager.create_agent(
            name="TestAgent",
            instructions="You are a test agent.",
        )

        mock_client.agents_client.create_agent.assert_called_once_with(
            model="gpt-4-1",
            name="TestAgent",
            instructions="You are a test agent.",
        )
        assert result.id == "agent-001"

    def test_uses_custom_model_deployment(self):
        """create_agent should respect an explicit ``model`` override."""
        mock_client = _make_mock_client(model="gpt-4-1")
        mock_client.agents_client.create_agent.return_value = _make_mock_agent()

        manager = AgentManager(mock_client)
        manager.create_agent(
            name="CustomModel",
            instructions="test",
            model="gpt-4o-mini",
        )

        call_kwargs = mock_client.agents_client.create_agent.call_args
        assert call_kwargs[1]["model"] == "gpt-4o-mini"


# ── Test: enable_auto_function_calls ────────────────────────────


class TestEnableAutoFunctionCalls:
    """Verify the v2 ``enable_auto_function_calls`` is invoked when a ToolSet is provided."""

    def test_enable_auto_function_calls_with_toolset(self):
        """When a ``ToolSet`` is provided, ``enable_auto_function_calls``
        must be called on the agents client."""
        mock_client = _make_mock_client()
        mock_client.agents_client.create_agent.return_value = _make_mock_agent()

        toolset = ToolSet()
        manager = AgentManager(mock_client)
        manager.create_agent(
            name="WithTools",
            instructions="test",
            toolset=toolset,
        )

        mock_client.agents_client.enable_auto_function_calls.assert_called_once_with(toolset)

    def test_no_auto_function_calls_without_toolset(self):
        """When no toolset is provided, ``enable_auto_function_calls`` must NOT be called."""
        mock_client = _make_mock_client()
        mock_client.agents_client.create_agent.return_value = _make_mock_agent()

        manager = AgentManager(mock_client)
        manager.create_agent(name="NoTools", instructions="test")

        mock_client.agents_client.enable_auto_function_calls.assert_not_called()


# ── Test: delete_agent ──────────────────────────────────────────


class TestDeleteAgentV2:
    """Verify delete_agent calls the flat ``delete_agent`` on agents_client."""

    def test_calls_flat_delete_agent(self):
        mock_client = _make_mock_client()
        manager = AgentManager(mock_client)
        manager.delete_agent("agent-xyz")

        mock_client.agents_client.delete_agent.assert_called_once_with("agent-xyz")

    def test_delete_agent_handles_error_gracefully(self):
        """delete_agent should log a warning but NOT raise on failure."""
        mock_client = _make_mock_client()
        mock_client.agents_client.delete_agent.side_effect = Exception("Not found")

        manager = AgentManager(mock_client)
        # Should not raise
        manager.delete_agent("agent-missing")


# ── Test: threads / messages sub-operations ─────────────────────


class TestThreadAndMessageSubOps:
    """Verify threads and messages use v2 sub-operation attributes."""

    def test_create_thread_uses_threads_sub_op(self):
        """create_thread must call ``agents_client.threads.create()``."""
        mock_client = _make_mock_client()
        mock_thread = _make_mock_thread()
        mock_client.agents_client.threads.create.return_value = mock_thread

        manager = AgentManager(mock_client)
        result = manager.create_thread()

        mock_client.agents_client.threads.create.assert_called_once()
        assert result.id == "thread-001"

    def test_add_message_uses_messages_sub_op(self):
        """add_message must call ``agents_client.messages.create()``."""
        mock_client = _make_mock_client()
        manager = AgentManager(mock_client)
        manager.add_message("thread-001", role="user", content="Hello agent")

        mock_client.agents_client.messages.create.assert_called_once_with(
            thread_id="thread-001",
            role="user",
            content="Hello agent",
        )


# ── Test: run_agent uses v2 patterns ────────────────────────────


class TestRunAgentV2:
    """Verify run_agent uses v2 ``runs.create_and_process`` and message extraction."""

    def test_run_agent_calls_create_and_process(self):
        """run_agent must use ``runs.create_and_process`` (v2 pattern)."""
        mock_client = _make_mock_client()
        mock_thread = _make_mock_thread()
        mock_client.agents_client.threads.create.return_value = mock_thread
        mock_client.agents_client.runs.create_and_process.return_value = _make_successful_run()
        mock_client.agents_client.messages.get_last_message_text_by_role.return_value = (
            "The VIN decodes to a 2003 Honda Accord."
        )

        manager = AgentManager(mock_client)
        result = manager.run_agent("agent-001", "Decode VIN: 1HGCM82633A004352")

        mock_client.agents_client.runs.create_and_process.assert_called_once_with(
            thread_id="thread-001",
            agent_id="agent-001",
        )
        assert result == "The VIN decodes to a 2003 Honda Accord."

    def test_run_agent_uses_get_last_message_text_by_role(self):
        """Response extraction must use the v2 ``get_last_message_text_by_role`` helper."""
        mock_client = _make_mock_client()
        mock_thread = _make_mock_thread()
        mock_client.agents_client.threads.create.return_value = mock_thread
        mock_client.agents_client.runs.create_and_process.return_value = _make_successful_run()
        mock_client.agents_client.messages.get_last_message_text_by_role.return_value = "Hello"

        manager = AgentManager(mock_client)
        manager.run_agent("agent-001", "Hi")

        mock_client.agents_client.messages.get_last_message_text_by_role.assert_called_once_with(
            thread_id="thread-001",
            role=MessageRole.AGENT,
        )

    def test_run_agent_failed_raises_runtime_error(self):
        """A failed agent run should raise ``RuntimeError``."""
        mock_client = _make_mock_client()
        mock_thread = _make_mock_thread()
        mock_client.agents_client.threads.create.return_value = mock_thread
        mock_client.agents_client.runs.create_and_process.return_value = _make_failed_run(
            "Model overloaded"
        )

        manager = AgentManager(mock_client)

        with pytest.raises(RuntimeError, match="Model overloaded"):
            manager.run_agent("agent-001", "Hello")

    def test_run_agent_reuses_existing_thread(self):
        """When ``thread_id`` is provided, no new thread should be created."""
        mock_client = _make_mock_client()
        mock_client.agents_client.runs.create_and_process.return_value = _make_successful_run()
        mock_client.agents_client.messages.get_last_message_text_by_role.return_value = "Reply"

        manager = AgentManager(mock_client)
        manager.run_agent("agent-001", "Follow-up question", thread_id="existing-thread")

        # threads.create should NOT have been called
        mock_client.agents_client.threads.create.assert_not_called()
        # But the run should use the existing thread
        mock_client.agents_client.runs.create_and_process.assert_called_once_with(
            thread_id="existing-thread",
            agent_id="agent-001",
        )

    def test_get_last_assistant_message_returns_empty_on_none(self):
        """If the v2 helper returns ``None``, the method should return ``""``."""
        mock_client = _make_mock_client()
        mock_client.agents_client.messages.get_last_message_text_by_role.return_value = None

        manager = AgentManager(mock_client)
        result = manager._get_last_assistant_message("thread-001")

        assert result == ""


# ── Test: temporary_agent context manager ───────────────────────


class TestTemporaryAgent:
    """Verify the context manager creates and cleans up the agent."""

    def test_temporary_agent_creates_and_deletes(self):
        """Exiting the context manager must call ``delete_agent``."""
        mock_client = _make_mock_client()
        mock_agent = _make_mock_agent("temp-agent-99")
        mock_client.agents_client.create_agent.return_value = mock_agent

        manager = AgentManager(mock_client)

        with manager.temporary_agent(name="Temp", instructions="test") as agent:
            assert agent.id == "temp-agent-99"

        mock_client.agents_client.delete_agent.assert_called_once_with("temp-agent-99")

    def test_temporary_agent_deletes_on_exception(self):
        """Even if the body raises, the agent should still be deleted."""
        mock_client = _make_mock_client()
        mock_client.agents_client.create_agent.return_value = _make_mock_agent("temp-err")

        manager = AgentManager(mock_client)

        with pytest.raises(ValueError, match="boom"):
            with manager.temporary_agent(name="Temp", instructions="test"):
                raise ValueError("boom")

        mock_client.agents_client.delete_agent.assert_called_once_with("temp-err")


# ── Test: retry logic ───────────────────────────────────────────


class TestRetryLogic:
    """Verify 429 retry-after handling."""

    @patch("foundrykit.agent.time.sleep")
    def test_retries_on_429(self, mock_sleep):
        """A 429 response should be retried after the Retry-After header delay."""
        mock_response = MagicMock()
        mock_response.headers = {"Retry-After": "1"}

        error_429 = HttpResponseError(response=mock_response)
        error_429.status_code = 429

        call_count = 0

        def fn():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error_429
            return "success"

        result = AgentManager._retry(fn, max_retries=3)

        assert result == "success"
        assert call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_raises_non_429_immediately(self):
        """Non-429 HTTP errors should NOT be retried."""
        mock_response = MagicMock()
        mock_response.headers = {}

        error_500 = HttpResponseError(response=mock_response)
        error_500.status_code = 500

        with pytest.raises(HttpResponseError):
            AgentManager._retry(lambda: (_ for _ in ()).throw(error_500), max_retries=3)


# ── Test: AgentStreamEvent dataclass ────────────────────────────


class TestAgentStreamEvent:
    """Verify the dataclass defaults."""

    def test_defaults(self):
        event = AgentStreamEvent(event_type="text_delta")
        assert event.data == ""
        assert event.metadata == {}

    def test_custom_values(self):
        event = AgentStreamEvent(
            event_type="tool_start",
            data="Executing tools...",
            metadata={"step_id": "step-1"},
        )
        assert event.event_type == "tool_start"
        assert event.metadata["step_id"] == "step-1"
