"""Agent lifecycle manager — create, run, and clean up Foundry Prompt Agents.

Uses the ``AgentsClient`` (v2 SDK) directly with flat methods and the
``enable_auto_function_calls`` helper for automatic tool invocation.

Includes structured logging, OTel tracing, retry-after handling for 429s,
and context-manager cleanup.

Usage::

    from foundrykit import AgentManager, get_foundry_client

    client = get_foundry_client()
    manager = AgentManager(client)

    agent = manager.create_agent(
        name="VINInsight",
        instructions="You are an automotive analyst...",
        toolset=toolset,
    )

    # Synchronous
    result = manager.run_agent(agent.id, user_message="Decode VIN: 1HGCM82633A004352")
    print(result)

    # Streaming
    for event in manager.run_agent_stream(agent.id, user_message="Decode VIN: ..."):
        if event.event_type == "text_delta":
            print(event.data, end="", flush=True)

    manager.cleanup(agent.id)
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from azure.ai.agents.models import (
    AgentEventHandler,
    MessageDeltaChunk,
    MessageDeltaTextContent,
    MessageRole,
    RequiredMcpToolCall,
    RunStep,
    SubmitToolApprovalAction,
    ThreadRun,
    ToolApproval,
    ToolSet,
)
from azure.core.exceptions import HttpResponseError
from opentelemetry import trace

if TYPE_CHECKING:
    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import Agent, AgentThread, RunHandler

    from foundrykit.client import FoundryClient

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("foundrykit.agent")

# Maximum retries for 429 rate-limit errors
_MAX_RETRIES = 3


# ── Stream Event dataclass ──────────────────────────────────────


@dataclass
class AgentStreamEvent:
    """A single event yielded during a streaming agent run.

    :param event_type: One of ``"text_delta"``, ``"tool_start"``,
        ``"tool_complete"``, ``"run_completed"``, ``"error"``.
    :param data: The text chunk (for ``text_delta``) or descriptive info.
    :param metadata: Optional extra metadata (tool name, run status, etc.).
    """

    event_type: str
    data: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentManager:
    """Lifecycle helpers for Foundry Prompt Agents.

    :param client: A ``FoundryClient`` instance providing the agents client.
    """

    def __init__(self, client: FoundryClient) -> None:
        self._client = client

    @property
    def _agents(self) -> AgentsClient:
        """Shortcut to the underlying ``AgentsClient``."""
        return self._client.agents_client

    # ── Agent CRUD ──────────────────────────────────────────────

    def create_agent(
        self,
        *,
        name: str,
        instructions: str,
        toolset: Any | None = None,
        model: str | None = None,
    ) -> Agent:
        """Create a new Foundry Prompt Agent.

        :param name: Agent name (alphanumeric + hyphens, max 63 chars).
        :param instructions: System prompt / instructions for the agent.
        :param toolset: Optional ``ToolSet`` with registered tools.
        :param model: Model deployment name.  Defaults to the configured deployment.
        :return: The created ``Agent`` object.
        :raises HttpResponseError: On Azure API errors (including 429).
        """
        deployment = model or self._client.model_deployment

        with tracer.start_as_current_span("foundrykit.create_agent") as span:
            span.set_attribute("agent.name", name)
            span.set_attribute("agent.model", deployment)

            logger.info("creating_agent", name=name, model=deployment)

            kwargs: dict[str, Any] = {
                "model": deployment,
                "name": name,
                "instructions": instructions,
            }
            if toolset is not None:
                kwargs["toolset"] = toolset

            agent = self._retry(
                lambda: self._agents.create_agent(**kwargs)
            )

            # v2 SDK: register the toolset for automatic local function
            # execution during create_and_process() and stream() calls.
            if toolset is not None and isinstance(toolset, ToolSet):
                self._agents.enable_auto_function_calls(toolset)
                logger.debug("auto_function_calls_enabled")

            span.set_attribute("agent.id", agent.id)
            logger.info("agent_created", name=name, agent_id=agent.id)
            return agent

    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent by ID.

        :param agent_id: The agent's unique identifier.
        """
        with tracer.start_as_current_span("foundrykit.delete_agent") as span:
            span.set_attribute("agent.id", agent_id)
            try:
                self._agents.delete_agent(agent_id)
                logger.info("agent_deleted", agent_id=agent_id)
            except Exception as e:
                logger.warning("agent_delete_failed", agent_id=agent_id, error=str(e))

    # ── Thread + Message ────────────────────────────────────────

    def create_thread(self) -> AgentThread:
        """Create a new conversation thread.

        :return: The created thread object.
        """
        with tracer.start_as_current_span("foundrykit.create_thread"):
            thread = self._agents.threads.create()
            logger.info("thread_created", thread_id=thread.id)
            return thread

    def add_message(self, thread_id: str, *, role: str = "user", content: str) -> None:
        """Add a message to a thread.

        :param thread_id: Target thread ID.
        :param role: Message role (``"user"`` or ``"assistant"``).
        :param content: Message text.
        """
        with tracer.start_as_current_span("foundrykit.add_message") as span:
            span.set_attribute("thread.id", thread_id)
            span.set_attribute("message.role", role)
            self._agents.messages.create(
                thread_id=thread_id,
                role=role,
                content=content,
            )
            logger.info("message_added", thread_id=thread_id, role=role)

    # ── Run Agent ───────────────────────────────────────────────

    def run_agent(
        self,
        agent_id: str,
        user_message: str,
        *,
        thread_id: str | None = None,
        run_handler: RunHandler | None = None,
    ) -> str:
        """Send a message and run the agent to completion.

        Creates a new thread if ``thread_id`` is not provided.  Returns the
        agent's final text response.

        :param agent_id: The agent to run.
        :param user_message: The user's input message.
        :param thread_id: Optional existing thread ID for multi-turn conversations.
        :param run_handler: Optional ``RunHandler`` for MCP tool-call approval.
            Pass a ``McpRunHandler`` instance when using MCP tools.
        :return: The agent's text response.
        :raises RuntimeError: If the agent run fails.
        """
        with tracer.start_as_current_span("foundrykit.run_agent") as span:
            span.set_attribute("agent.id", agent_id)

            # Create or reuse thread
            if thread_id is None:
                thread = self.create_thread()
                thread_id = thread.id
            span.set_attribute("thread.id", thread_id)

            # Send user message
            self.add_message(thread_id, role="user", content=user_message)

            # Execute the agent run (processes tool calls automatically)
            logger.info(
                "agent_run_start",
                agent_id=agent_id,
                thread_id=thread_id,
            )

            create_kwargs: dict[str, Any] = {
                "thread_id": thread_id,
                "agent_id": agent_id,
            }
            if run_handler is not None:
                create_kwargs["run_handler"] = run_handler

            run = self._retry(
                lambda: self._agents.runs.create_and_process(**create_kwargs)
            )

            if run.status == "failed":
                error_msg = run.last_error or "Unknown agent run failure"
                logger.error(
                    "agent_run_failed",
                    agent_id=agent_id,
                    thread_id=thread_id,
                    error=str(error_msg),
                )
                span.set_attribute("agent.run.error", str(error_msg))
                raise RuntimeError(f"Agent run failed: {error_msg}")

            logger.info(
                "agent_run_complete",
                agent_id=agent_id,
                thread_id=thread_id,
                status=run.status,
            )

            # Extract the assistant's final response
            return self._get_last_assistant_message(thread_id)

    # ── Streaming Run ───────────────────────────────────────────

    def run_agent_stream(
        self,
        agent_id: str,
        user_message: str,
        *,
        thread_id: str | None = None,
        mcp_tools: list[Any] | None = None,
    ) -> Generator[AgentStreamEvent, None, None]:
        """Send a message and stream events as the agent executes.

        Uses ``runs.stream()`` with :class:`AgentEventHandler` so that tool
        calls are handled automatically.  Yields :class:`AgentStreamEvent`
        instances for each text delta, tool activity, and completion.

        :param agent_id: The agent to run.
        :param user_message: The user's input message.
        :param thread_id: Optional existing thread for multi-turn.
        :param mcp_tools: Optional list of ``McpTool`` instances.  When
            provided, the stream handler will auto-approve MCP tool calls
            and forward headers from the supplied tools.
        :return: Generator of :class:`AgentStreamEvent`.
        :raises RuntimeError: If the agent run fails.
        """
        with tracer.start_as_current_span("foundrykit.run_agent_stream") as span:
            span.set_attribute("agent.id", agent_id)

            if thread_id is None:
                thread = self.create_thread()
                thread_id = thread.id
            span.set_attribute("thread.id", thread_id)

            self.add_message(thread_id, role="user", content=user_message)

            logger.info("agent_stream_start", agent_id=agent_id, thread_id=thread_id)

            collector = _StreamCollector(
                agents_client=self._agents,
                mcp_tools=mcp_tools,
            )

            with self._agents.runs.stream(
                thread_id=thread_id,
                agent_id=agent_id,
                event_handler=collector,
            ) as stream:
                for _event_type, _event_data, _func_return in stream:
                    pass  # events are captured by the collector callbacks

            # Yield all collected events
            yield from collector.events

            logger.info(
                "agent_stream_complete",
                agent_id=agent_id,
                thread_id=thread_id,
                event_count=len(collector.events),
            )

    def _get_last_assistant_message(self, thread_id: str) -> str:
        """Extract the last assistant message from a thread.

        Uses the v2 SDK helper ``get_last_message_text_by_role`` for clean
        extraction.

        :param thread_id: Thread to read messages from.
        :return: Text content of the last assistant message.
        """
        last_text = self._agents.messages.get_last_message_text_by_role(
            thread_id=thread_id,
            role=MessageRole.AGENT,
        )
        return last_text or ""

    # ── Context Manager ─────────────────────────────────────────

    @contextmanager
    def temporary_agent(
        self,
        *,
        name: str,
        instructions: str,
        toolset: Any | None = None,
        model: str | None = None,
    ):
        """Context manager that creates an agent and deletes it on exit.

        :param name: Agent name.
        :param instructions: Agent instructions / system prompt.
        :param toolset: Optional ``ToolSet``.
        :param model: Optional model deployment override.
        :return: Yields the created ``Agent``.
        """
        agent = self.create_agent(
            name=name,
            instructions=instructions,
            toolset=toolset,
            model=model,
        )
        try:
            yield agent
        finally:
            self.delete_agent(agent.id)

    # ── Retry Helper ────────────────────────────────────────────

    @staticmethod
    def _retry(fn, max_retries: int = _MAX_RETRIES):
        """Execute *fn* with retry-after handling for 429 responses.

        :param fn: Callable to execute.
        :param max_retries: Maximum number of retries.
        :return: Result of *fn*.
        :raises HttpResponseError: If retries are exhausted.
        """
        for attempt in range(1, max_retries + 1):
            try:
                return fn()
            except HttpResponseError as e:
                if e.status_code == 429 and attempt < max_retries:
                    retry_after = int(e.response.headers.get("Retry-After", "5"))
                    logger.warning(
                        "rate_limited",
                        attempt=attempt,
                        retry_after=retry_after,
                    )
                    time.sleep(retry_after)
                else:
                    raise


# ── Stream Collector Event Handler ──────────────────────────────


class _StreamCollector(AgentEventHandler):
    """Collects streaming events into a list of :class:`AgentStreamEvent`.

    The ``AgentEventHandler`` base class automatically processes tool calls
    via ``submit_tool_outputs``, so this handler only needs to capture the
    text deltas and lifecycle events.

    When ``mcp_tools`` are provided, MCP tool-call approvals are handled
    automatically by intercepting ``SubmitToolApprovalAction`` in
    ``on_thread_run``.
    """

    def __init__(
        self,
        agents_client: AgentsClient | None = None,
        mcp_tools: list[Any] | None = None,
    ) -> None:
        super().__init__()
        self.events: list[AgentStreamEvent] = []
        self._agents_client = agents_client
        self._mcp_tools = mcp_tools or []
        # Merge headers from all MCP tools
        self._mcp_headers: dict[str, str] = {}
        for mcp in self._mcp_tools:
            if hasattr(mcp, "headers") and mcp.headers:
                self._mcp_headers.update(mcp.headers)

    def on_message_delta(self, delta: MessageDeltaChunk) -> None:
        """Capture text delta chunks from the agent response.

        :param delta: The message delta chunk from the stream.
        """
        if delta.delta and delta.delta.content:
            for part in delta.delta.content:
                if isinstance(part, MessageDeltaTextContent) and part.text and part.text.value:
                    self.events.append(
                        AgentStreamEvent(event_type="text_delta", data=part.text.value)
                    )

    def on_thread_run(self, run: ThreadRun) -> None:
        """Capture run lifecycle events and handle MCP tool approvals.

        When the run status is ``requires_action`` with a
        ``SubmitToolApprovalAction``, this method auto-approves MCP tool
        calls and re-submits them via ``submit_tool_outputs_stream``.

        :param run: The thread run object with status updates.
        """
        # Handle MCP tool-call approval
        if (
            self._mcp_tools
            and self._agents_client
            and isinstance(run.required_action, SubmitToolApprovalAction)
        ):
            tool_calls = run.required_action.submit_tool_approval.tool_calls
            if tool_calls:
                tool_approvals = []
                for tc in tool_calls:
                    if isinstance(tc, RequiredMcpToolCall):
                        logger.info("mcp_stream_approval", tool_call_id=tc.id)
                        tool_approvals.append(
                            ToolApproval(
                                tool_call_id=tc.id,
                                approve=True,
                                headers=self._mcp_headers or None,
                            )
                        )
                        self.events.append(
                            AgentStreamEvent(
                                event_type="mcp_approved",
                                data=f"Approved MCP tool call {tc.id}",
                                metadata={"tool_call_id": tc.id},
                            )
                        )
                if tool_approvals:
                    self._agents_client.runs.submit_tool_outputs_stream(
                        thread_id=run.thread_id,
                        run_id=run.id,
                        tool_approvals=tool_approvals,
                        event_handler=self,
                    )
            return

        if run.status == "failed":
            error_msg = str(run.last_error) if run.last_error else "Agent run failed"
            self.events.append(
                AgentStreamEvent(event_type="error", data=error_msg)
            )
            logger.error("agent_stream_run_failed", error=error_msg)
        elif run.status == "completed":
            self.events.append(
                AgentStreamEvent(event_type="run_completed", data="")
            )

    def on_run_step(self, step: RunStep) -> None:
        """Capture tool execution steps for observability.

        :param step: The run step (tool_calls or message_creation).
        """
        if step.type == "tool_calls" and step.status == "in_progress":
            self.events.append(
                AgentStreamEvent(
                    event_type="tool_start",
                    data="Executing tools...",
                    metadata={"step_id": step.id},
                )
            )
        elif step.type == "tool_calls" and step.status == "completed":
            self.events.append(
                AgentStreamEvent(
                    event_type="tool_complete",
                    data="Tools completed.",
                    metadata={"step_id": step.id},
                )
            )

    def on_error(self, data: str) -> None:
        """Capture stream-level errors.

        :param data: Error information from the stream.
        """
        self.events.append(
            AgentStreamEvent(event_type="error", data=str(data))
        )
        logger.error("agent_stream_error", error=str(data))

    def on_done(self) -> None:
        """Signal that the stream is complete."""
        pass  # run_completed event already emitted by on_thread_run
