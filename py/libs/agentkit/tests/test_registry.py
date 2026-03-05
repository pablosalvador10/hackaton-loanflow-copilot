"""Tests for agentkit.registry — ToolRegistry."""

from __future__ import annotations

import pytest

from agentkit.registry import ToolDefinition, ToolRegistry


@pytest.fixture
def registry() -> ToolRegistry:
    """Fresh registry for each test."""
    return ToolRegistry()


class TestToolDecorator:
    """@registry.tool() decorator."""

    def test_register_sync_function(self, registry: ToolRegistry):
        @registry.tool()
        def greet(name: str) -> str:
            """Greet by name.

            :param name: Person's name.
            """
            return f"Hello, {name}!"

        assert registry.tool_count == 1
        assert "greet" in registry.list_tools()

    def test_register_async_function(self, registry: ToolRegistry):
        @registry.tool()
        async def greet_async(name: str) -> str:
            """Greet asynchronously."""
            return f"Hello, {name}!"

        assert registry.tool_count == 1

    def test_register_with_custom_name(self, registry: ToolRegistry):
        @registry.tool(name="custom_greet")
        def greet(name: str) -> str:
            """Greet."""
            return f"Hello, {name}!"

        assert "custom_greet" in registry.list_tools()
        assert "greet" not in registry.list_tools()

    def test_register_as_handoff(self, registry: ToolRegistry):
        @registry.tool(is_handoff=True)
        async def handoff_fraud(reason: str = "") -> dict:
            """Transfer to fraud agent."""
            return {"handoff": True, "target_agent": "FraudAgent"}

        assert registry.is_handoff_tool("handoff_fraud") is True

    def test_register_with_tags(self, registry: ToolRegistry):
        @registry.tool(tags={"banking", "accounts"})
        def get_balance(account_id: str) -> dict:
            """Get balance."""
            return {"balance": 100.0}

        tools_banking = registry.list_tools(tags={"banking"})
        assert "get_balance" in tools_banking

    def test_schema_auto_generated(self, registry: ToolRegistry):
        @registry.tool()
        def add(a: int, b: int) -> int:
            """Add two numbers.

            :param a: First number.
            :param b: Second number.
            """
            return a + b

        defn = registry.get_definition("add")
        assert defn is not None
        schema = defn.schema
        assert schema["name"] == "add"
        assert "Add two numbers" in schema["description"]
        assert "a" in schema["parameters"]["properties"]
        assert "b" in schema["parameters"]["properties"]
        assert schema["parameters"]["properties"]["a"]["type"] == "integer"
        assert "a" in schema["parameters"]["required"]


class TestImperativeRegistration:
    """registry.register() method."""

    def test_register_explicit(self, registry: ToolRegistry):
        schema = {
            "name": "my_tool",
            "description": "A test tool.",
            "parameters": {"type": "object", "properties": {}},
        }

        def executor(**kwargs):
            return {"ok": True}

        registry.register("my_tool", schema, executor)
        assert registry.tool_count == 1
        assert registry.get_definition("my_tool") is not None

    def test_no_override_by_default(self, registry: ToolRegistry):
        schema = {
            "name": "dup",
            "description": "First.",
            "parameters": {"type": "object", "properties": {}},
        }
        registry.register("dup", schema, lambda: None)
        registry.register(
            "dup",
            {**schema, "description": "Second."},
            lambda: None,
        )
        # Should still be "First."
        assert registry.get_definition("dup").description == "First."

    def test_override_when_explicit(self, registry: ToolRegistry):
        schema = {
            "name": "dup",
            "description": "First.",
            "parameters": {"type": "object", "properties": {}},
        }
        registry.register("dup", schema, lambda: None)
        registry.register(
            "dup",
            {**schema, "description": "Second."},
            lambda: None,
            override=True,
        )
        assert registry.get_definition("dup").description == "Second."


class TestHandoffRegistration:
    """register_handoff() and register_generic_handoff()."""

    def test_register_handoff(self, registry: ToolRegistry):
        registry.register_handoff(
            "handoff_support",
            target_agent="SupportAgent",
            description="Transfer to support.",
        )
        assert registry.is_handoff_tool("handoff_support") is True
        defn = registry.get_definition("handoff_support")
        assert defn is not None
        assert "reason" in defn.schema["parameters"]["properties"]

    def test_register_generic_handoff(self, registry: ToolRegistry):
        registry.register_generic_handoff()
        assert registry.is_handoff_tool("handoff_to_agent") is True
        defn = registry.get_definition("handoff_to_agent")
        assert "target_agent" in defn.schema["parameters"]["properties"]


class TestGetToolsForAgent:
    """get_tools_for_agent() method."""

    def test_returns_openai_format(self, registry: ToolRegistry):
        @registry.tool()
        def tool_a() -> str:
            """Tool A."""
            return "a"

        @registry.tool()
        def tool_b() -> str:
            """Tool B."""
            return "b"

        tools = registry.get_tools_for_agent(["tool_a", "tool_b"])
        assert len(tools) == 2
        assert all(t["type"] == "function" for t in tools)
        names = {t["function"]["name"] for t in tools}
        assert names == {"tool_a", "tool_b"}

    def test_missing_tool_returns_empty(self, registry: ToolRegistry):
        tools = registry.get_tools_for_agent(["nonexistent"])
        assert tools == []


class TestExecute:
    """Tool execution."""

    @pytest.mark.asyncio
    async def test_execute_sync(self, registry: ToolRegistry):
        @registry.tool()
        def add(a: int, b: int) -> dict:
            """Add."""
            return {"sum": a + b}

        result = await registry.execute("add", {"a": 2, "b": 3})
        assert result["sum"] == 5

    @pytest.mark.asyncio
    async def test_execute_async(self, registry: ToolRegistry):
        @registry.tool()
        async def greet(name: str) -> dict:
            """Greet."""
            return {"greeting": f"Hello, {name}!"}

        result = await registry.execute("greet", {"name": "Alice"})
        assert result["greeting"] == "Hello, Alice!"

    @pytest.mark.asyncio
    async def test_execute_not_found(self, registry: ToolRegistry):
        result = await registry.execute("missing", {})
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_handoff(self, registry: ToolRegistry):
        registry.register_handoff(
            "handoff_test", target_agent="TestAgent"
        )
        result = await registry.execute("handoff_test", {"reason": "test"})
        assert result["handoff"] is True
        assert result["target_agent"] == "TestAgent"


class TestListAndFilter:
    """list_tools() filtering."""

    def test_list_all(self, registry: ToolRegistry):
        @registry.tool()
        def a():
            """A."""
            ...

        @registry.tool(is_handoff=True)
        async def b():
            """B."""
            ...

        assert len(registry.list_tools()) == 2

    def test_list_handoffs_only(self, registry: ToolRegistry):
        @registry.tool()
        def a():
            """A."""
            ...

        @registry.tool(is_handoff=True)
        async def b():
            """B."""
            ...

        handoffs = registry.list_tools(handoffs_only=True)
        assert handoffs == ["b"]

    def test_list_by_tags(self, registry: ToolRegistry):
        @registry.tool(tags={"banking"})
        def a():
            """A."""
            ...

        @registry.tool(tags={"support"})
        def b():
            """B."""
            ...

        assert registry.list_tools(tags={"banking"}) == ["a"]


class TestReset:
    """Registry reset."""

    def test_reset_clears_all(self, registry: ToolRegistry):
        @registry.tool()
        def a():
            """A."""
            ...

        assert registry.tool_count == 1
        registry.reset()
        assert registry.tool_count == 0
