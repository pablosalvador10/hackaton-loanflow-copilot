"""Multi-agent orchestrator — manages conversation flow, tool calls, and handoffs.

The ``Orchestrator`` is the execution engine that ties agents, tools, and
scenarios together.  It uses the OpenAI Chat Completions API (or any
compatible API) to drive conversations.

Architecture (from the ART Voice Agent Cascade pattern):

1. Receive user message.
2. Build system prompt from the active agent's template + scenario handoff instructions.
3. Call LLM with tools from the agent's tool list.
4. If the LLM calls a handoff tool → switch active agent, re-call LLM.
5. If the LLM calls a business tool → execute via registry, feed result back.
6. Return final text response.

Supports both single-turn and streaming modes.

Usage::

    from agentkit import Orchestrator, ToolRegistry, AgentLoader

    registry = ToolRegistry()
    loader = AgentLoader("./agents", tool_registry=registry)
    agents = loader.discover()

    orchestrator = Orchestrator(
        agents=agents,
        tool_registry=registry,
        model="gpt-4o",
    )

    # Single-turn
    result = await orchestrator.run("What's my balance?")
    print(result.text)

    # Streaming
    async for event in orchestrator.stream("What's my balance?"):
        if event.type == "text_delta":
            print(event.data, end="")
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import structlog
from openai import AsyncOpenAI
from opentelemetry import trace

from agentkit.agent import Agent, build_handoff_map
from agentkit.registry import ToolRegistry
from agentkit.scenario import ScenarioConfig

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("agentkit.orchestrator")


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TurnContext:
    """Mutable context bag for a single orchestrator turn.

    Passed to tool executions and available for inspection after the turn.

    :param system_vars: Variables injected into prompt rendering.
    :param active_agent: Currently active agent name.
    :param visited_agents: Set of agents visited in this session.
    :param handoff_history: List of ``(from, to, reason)`` tuples.
    :param tool_outputs: Results from tool executions in this turn.
    """

    system_vars: dict[str, Any] = field(default_factory=dict)
    active_agent: str = ""
    visited_agents: set[str] = field(default_factory=set)
    handoff_history: list[tuple[str, str, str]] = field(default_factory=list)
    tool_outputs: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorResult:
    """Result of a single orchestrator turn.

    :param text: The agent's text response.
    :param agent_name: Name of the agent that produced the response.
    :param tool_calls: List of tool calls made during this turn.
    :param handoff_occurred: Whether an agent handoff occurred.
    :param context: The full turn context.
    """

    text: str
    agent_name: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    handoff_occurred: bool = False
    context: TurnContext = field(default_factory=TurnContext)


@dataclass
class StreamEvent:
    """A streaming event from the orchestrator.

    :param type: Event type (``text_delta``, ``tool_start``, ``tool_complete``,
                 ``handoff``, ``error``, ``done``).
    :param data: Event payload.
    :param metadata: Optional metadata.
    """

    type: str
    data: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════


class Orchestrator:
    """Multi-agent orchestrator using OpenAI Chat Completions.

    Manages the conversation loop: prompt rendering, LLM calls, tool
    execution, and agent handoffs.

    :param agents: Dict of ``agent_name → Agent``.
    :param tool_registry: The tool registry containing all tool implementations.
    :param client: An ``AsyncOpenAI`` client (or compatible). If not provided,
                   creates one from environment variables.
    :param model: Default model name (overridden by per-agent config).
    :param scenario: Optional scenario config for multi-agent handoffs.
    :param start_agent: Starting agent name. Defaults to the first agent
                        with ``handoff.is_entry_point=True`` or the first agent.
    :param max_tool_rounds: Maximum tool-call rounds per turn (prevents loops).
    """

    def __init__(
        self,
        agents: dict[str, Agent],
        tool_registry: ToolRegistry,
        *,
        client: AsyncOpenAI | None = None,
        model: str = "gpt-4o",
        scenario: ScenarioConfig | None = None,
        start_agent: str | None = None,
        max_tool_rounds: int = 10,
    ) -> None:
        self._agents = agents
        self._registry = tool_registry
        self._client = client or AsyncOpenAI()
        self._default_model = model
        self._scenario = scenario
        self._max_tool_rounds = max_tool_rounds

        # Build handoff map from agent declarations + scenario edges
        self._handoff_map = build_handoff_map(agents)
        if scenario:
            self._handoff_map.update(scenario.build_handoff_map())

        # Determine start agent
        self._active_agent = start_agent or self._find_entry_point()
        self._visited_agents: set[str] = {self._active_agent}

        # Conversation history per agent
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Cross-agent message memory (for context retention)
        self._user_message_history: deque[str] = deque(maxlen=20)

    # ── Public API ──────────────────────────────────────────────────

    async def run(
        self,
        user_message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> OrchestratorResult:
        """Process a single user message and return the agent's response.

        :param user_message: The user's input.
        :param context: Optional runtime context for prompt rendering.
        :return: The orchestrator result.
        """
        with tracer.start_as_current_span("orchestrator.run") as span:
            span.set_attribute("user_message", user_message[:200])
            span.set_attribute("active_agent", self._active_agent)

            turn_ctx = TurnContext(
                system_vars=context or {},
                active_agent=self._active_agent,
                visited_agents=set(self._visited_agents),
            )

            # Track user message
            self._user_message_history.append(user_message)
            self._history[self._active_agent].append(
                {"role": "user", "content": user_message}
            )

            all_tool_calls: list[dict[str, Any]] = []
            handoff_occurred = False

            for round_num in range(self._max_tool_rounds):
                agent = self._agents[self._active_agent]
                messages = self._build_messages(agent, turn_ctx)
                tools = self._registry.get_tools_for_agent(agent.tool_names)

                # Inject scenario handoff tools if needed
                tools = self._inject_handoff_tools(agent, tools)

                # Call LLM
                response = await self._call_llm(
                    agent, messages, tools, span
                )

                choice = response.choices[0]

                # Check for tool calls
                if choice.finish_reason == "tool_calls" or choice.message.tool_calls:
                    tool_results, is_handoff = await self._process_tool_calls(
                        choice.message.tool_calls, agent, turn_ctx, span
                    )
                    all_tool_calls.extend(tool_results)

                    if is_handoff:
                        handoff_occurred = True
                        # After handoff, loop back to call the new agent
                        continue

                    # Add tool results to history and continue for LLM to process
                    self._history[self._active_agent].append(
                        choice.message.model_dump()
                    )
                    for result in tool_results:
                        self._history[self._active_agent].append(
                            {
                                "role": "tool",
                                "tool_call_id": result["tool_call_id"],
                                "content": json.dumps(result["result"]),
                            }
                        )
                    continue

                # No tool calls — we have a final text response
                text = choice.message.content or ""
                self._history[self._active_agent].append(
                    {"role": "assistant", "content": text}
                )

                turn_ctx.active_agent = self._active_agent
                turn_ctx.visited_agents = set(self._visited_agents)

                span.set_attribute("response_agent", self._active_agent)
                span.set_attribute("handoff_occurred", handoff_occurred)

                return OrchestratorResult(
                    text=text,
                    agent_name=self._active_agent,
                    tool_calls=all_tool_calls,
                    handoff_occurred=handoff_occurred,
                    context=turn_ctx,
                )

            # Exhausted max rounds
            logger.warning(
                "max_tool_rounds_reached",
                agent=self._active_agent,
                rounds=self._max_tool_rounds,
            )
            return OrchestratorResult(
                text="I'm sorry, I wasn't able to complete your request. Please try again.",
                agent_name=self._active_agent,
                tool_calls=all_tool_calls,
                handoff_occurred=handoff_occurred,
                context=turn_ctx,
            )

    async def stream(
        self,
        user_message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream the agent's response as events.

        Yields ``StreamEvent`` instances as the response is generated.

        :param user_message: The user's input.
        :param context: Optional runtime context for prompt rendering.
        :yields: Stream events.
        """
        with tracer.start_as_current_span("orchestrator.stream") as span:
            span.set_attribute("user_message", user_message[:200])
            span.set_attribute("active_agent", self._active_agent)

            turn_ctx = TurnContext(
                system_vars=context or {},
                active_agent=self._active_agent,
                visited_agents=set(self._visited_agents),
            )

            self._user_message_history.append(user_message)
            self._history[self._active_agent].append(
                {"role": "user", "content": user_message}
            )

            for round_num in range(self._max_tool_rounds):
                agent = self._agents[self._active_agent]
                messages = self._build_messages(agent, turn_ctx)
                tools = self._registry.get_tools_for_agent(agent.tool_names)
                tools = self._inject_handoff_tools(agent, tools)

                # Stream LLM response
                collected_text = ""
                tool_calls_data: list[dict[str, Any]] = []
                current_tool_calls: dict[int, dict[str, Any]] = {}

                stream = await self._client.chat.completions.create(
                    model=agent.model.model or self._default_model,
                    messages=messages,
                    tools=tools or None,
                    temperature=agent.model.temperature,
                    max_tokens=agent.model.max_tokens,
                    stream=True,
                )

                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta

                    # Text content
                    if delta.content:
                        collected_text += delta.content
                        yield StreamEvent(
                            type="text_delta", data=delta.content
                        )

                    # Tool calls (accumulated across chunks)
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in current_tool_calls:
                                current_tool_calls[idx] = {
                                    "id": tc.id or "",
                                    "name": "",
                                    "arguments": "",
                                }
                            if tc.id:
                                current_tool_calls[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    current_tool_calls[idx]["name"] = (
                                        tc.function.name
                                    )
                                if tc.function.arguments:
                                    current_tool_calls[idx]["arguments"] += (
                                        tc.function.arguments
                                    )

                # Process any tool calls
                if current_tool_calls:
                    for idx in sorted(current_tool_calls.keys()):
                        tc_data = current_tool_calls[idx]
                        tool_name = tc_data["name"]
                        tool_call_id = tc_data["id"]

                        try:
                            args = json.loads(tc_data["arguments"])
                        except json.JSONDecodeError:
                            args = {}

                        yield StreamEvent(
                            type="tool_start",
                            data=tool_name,
                            metadata={"args": args},
                        )

                        # Check for handoff
                        if self._registry.is_handoff_tool(tool_name):
                            result = await self._registry.execute(
                                tool_name, args
                            )
                            target = self._resolve_handoff_target(
                                tool_name, result
                            )
                            if target and target in self._agents:
                                yield StreamEvent(
                                    type="handoff",
                                    data=target,
                                    metadata={
                                        "from": self._active_agent,
                                        "reason": result.get(
                                            "handoff_summary", ""
                                        ),
                                    },
                                )

                                # Switch agent
                                self._switch_agent(target, turn_ctx)

                                # Add assistant message with tool calls to history
                                self._history[self._active_agent].append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tool_call_id,
                                        "content": json.dumps(result),
                                    }
                                )
                                break  # Re-loop with new agent
                        else:
                            # Business tool
                            result = await self._registry.execute(
                                tool_name, args
                            )
                            yield StreamEvent(
                                type="tool_complete",
                                data=tool_name,
                                metadata={"result": result},
                            )

                            # Feed result back
                            tool_calls_data.append(
                                {
                                    "tool_call_id": tool_call_id,
                                    "name": tool_name,
                                    "result": result,
                                }
                            )

                    # If handoff occurred, continue to next round
                    if any(
                        self._registry.is_handoff_tool(
                            current_tool_calls[i]["name"]
                        )
                        for i in current_tool_calls
                    ):
                        continue

                    # Add tool results to history and re-call LLM
                    if tool_calls_data:
                        # Reconstruct the assistant message with tool_calls
                        assistant_tool_calls = []
                        for idx in sorted(current_tool_calls.keys()):
                            tc_data = current_tool_calls[idx]
                            assistant_tool_calls.append(
                                {
                                    "id": tc_data["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tc_data["name"],
                                        "arguments": tc_data["arguments"],
                                    },
                                }
                            )

                        self._history[self._active_agent].append(
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": assistant_tool_calls,
                            }
                        )
                        for td in tool_calls_data:
                            self._history[self._active_agent].append(
                                {
                                    "role": "tool",
                                    "tool_call_id": td["tool_call_id"],
                                    "content": json.dumps(td["result"]),
                                }
                            )
                        continue
                else:
                    # No tool calls — text response complete
                    if collected_text:
                        self._history[self._active_agent].append(
                            {"role": "assistant", "content": collected_text}
                        )
                    yield StreamEvent(
                        type="done",
                        data=self._active_agent,
                    )
                    return

            yield StreamEvent(
                type="error",
                data="Maximum tool rounds reached.",
            )

    # ── Agent switching ─────────────────────────────────────────────

    def switch_agent(self, agent_name: str) -> None:
        """Manually switch the active agent.

        :param agent_name: Name of the agent to switch to.
        :raises ValueError: If the agent is not registered.
        """
        if agent_name not in self._agents:
            raise ValueError(f"Agent '{agent_name}' not found.")
        self._active_agent = agent_name
        self._visited_agents.add(agent_name)

    @property
    def active_agent(self) -> str:
        """The currently active agent name."""
        return self._active_agent

    @property
    def visited_agents(self) -> set[str]:
        """Set of agents visited in this session."""
        return set(self._visited_agents)

    def reset(self) -> None:
        """Reset conversation state (history, visited agents)."""
        start = self._find_entry_point()
        self._active_agent = start
        self._visited_agents = {start}
        self._history.clear()
        self._user_message_history.clear()

    # ── Private helpers ─────────────────────────────────────────────

    def _find_entry_point(self) -> str:
        """Find the entry-point agent."""
        for agent in self._agents.values():
            if agent.handoff.is_entry_point:
                return agent.name

        if self._scenario and self._scenario.start_agent:
            return self._scenario.start_agent

        # Default to first agent
        return next(iter(self._agents))

    def _build_messages(
        self, agent: Agent, turn_ctx: TurnContext
    ) -> list[dict[str, Any]]:
        """Build the messages array for the LLM call."""
        # Render system prompt with context
        system_vars = {
            **turn_ctx.system_vars,
            "active_agent": self._active_agent,
            "visited_agents": list(self._visited_agents),
        }
        system_prompt = agent.render_prompt(system_vars)

        # Append scenario handoff instructions
        if self._scenario:
            handoff_instructions = self._scenario.build_handoff_instructions(
                agent.name
            )
            if handoff_instructions:
                system_prompt += "\n\n" + handoff_instructions

        # Inject cross-agent context
        context_section = self._build_context_section()
        if context_section:
            system_prompt += "\n\n" + context_section

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history for this agent
        messages.extend(self._history.get(self._active_agent, []))

        return messages

    def _build_context_section(self) -> str:
        """Build a conversation context section from cross-agent history."""
        if len(self._user_message_history) <= 1:
            return ""

        recent = list(self._user_message_history)[-5:]
        lines = ["## CONVERSATION CONTEXT", "Recent user messages:"]
        for msg in recent:
            lines.append(f"- {msg}")
        return "\n".join(lines)

    async def _call_llm(
        self,
        agent: Agent,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        span: trace.Span,
    ) -> Any:
        """Call the OpenAI Chat Completions API."""
        model = agent.model.model or self._default_model

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": agent.model.temperature,
            "max_tokens": agent.model.max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        span.set_attribute("gen_ai.model", model)
        span.set_attribute("gen_ai.agent.name", agent.name)

        response = await self._client.chat.completions.create(**kwargs)
        return response

    async def _process_tool_calls(
        self,
        tool_calls: list[Any],
        agent: Agent,
        turn_ctx: TurnContext,
        span: trace.Span,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Process tool calls from the LLM response.

        :return: Tuple of (tool results, whether a handoff occurred).
        """
        results: list[dict[str, Any]] = []
        handoff_occurred = False

        for tc in tool_calls:
            tool_name = tc.function.name
            tool_call_id = tc.id

            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            logger.info("tool_call", tool=tool_name, agent=agent.name)

            # Execute tool
            result = await self._registry.execute(tool_name, args)
            results.append(
                {
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "args": args,
                    "result": result,
                }
            )

            # Handle handoff
            if self._registry.is_handoff_tool(tool_name):
                target = self._resolve_handoff_target(tool_name, result)
                if target and target in self._agents:
                    logger.info(
                        "handoff",
                        from_agent=self._active_agent,
                        to_agent=target,
                    )
                    turn_ctx.handoff_history.append(
                        (self._active_agent, target, result.get("handoff_summary", ""))
                    )
                    self._switch_agent(target, turn_ctx)
                    handoff_occurred = True

            # Store tool output
            turn_ctx.tool_outputs[tool_name] = result

        return results, handoff_occurred

    def _resolve_handoff_target(
        self, tool_name: str, result: dict[str, Any]
    ) -> str | None:
        """Resolve the target agent from a handoff tool result."""
        # Check explicit target in result
        target = result.get("target_agent")
        if target:
            return target

        # Check handoff map
        return self._handoff_map.get(tool_name)

    def _switch_agent(self, target: str, turn_ctx: TurnContext) -> None:
        """Switch the active agent."""
        previous = self._active_agent
        self._active_agent = target
        self._visited_agents.add(target)
        turn_ctx.active_agent = target

        # Add previous agent context to system vars
        turn_ctx.system_vars["previous_agent"] = previous

        logger.info(
            "agent_switched",
            from_agent=previous,
            to_agent=target,
        )

    def _inject_handoff_tools(
        self, agent: Agent, tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Inject the generic handoff tool if the scenario requires it."""
        if not self._scenario:
            return tools

        tool_names = {
            t.get("function", {}).get("name") for t in tools
        }

        # Check if we need to add handoff_to_agent
        if "handoff_to_agent" not in tool_names:
            needs_handoff = False

            if self._scenario.generic_handoff.enabled:
                needs_handoff = True
            else:
                outgoing = self._scenario.get_outgoing_handoffs(agent.name)
                if outgoing:
                    needs_handoff = True

            if needs_handoff:
                handoff_tools = self._registry.get_tools_for_agent(
                    ["handoff_to_agent"]
                )
                tools = list(tools) + handoff_tools

        # Filter out explicit handoff tools (use generic instead)
        filtered: list[dict[str, Any]] = []
        for t in tools:
            name = t.get("function", {}).get("name", "")
            if name == "handoff_to_agent":
                filtered.append(t)
            elif not self._registry.is_handoff_tool(name):
                filtered.append(t)

        return filtered


__all__ = [
    "Orchestrator",
    "OrchestratorResult",
    "StreamEvent",
    "TurnContext",
]
