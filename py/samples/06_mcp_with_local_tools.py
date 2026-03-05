"""Sample 06: MCP + local function tools in the same agent.

Shows how to combine remote MCP tools (server-side, called by Azure)
with local Python function tools (client-side, auto-executed) in a
single ``ToolRegistry`` and ``ToolSet``.

The agent gets:
- MCP access to Azure REST API specs (remote)
- A local ``get_current_date`` function (local, auto-executed)
- A local ``calculate_days_until`` function (local, auto-executed)

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT        — Azure AI Foundry project endpoint.
    FOUNDRY_MODEL_DEPLOYMENT_NAME   — Model deployment (default: gpt-4-1).
"""

from datetime import datetime, timezone

from foundrykit import AgentManager, ToolRegistry, get_foundry_client, create_mcp_tool
from foundrykit.mcp import McpRunHandler


def main() -> None:
    client = get_foundry_client()
    manager = AgentManager(client)

    # ── 1. Create a ToolRegistry and register local functions ───
    registry = ToolRegistry()

    @registry.register
    def get_current_date() -> str:
        """Return the current UTC date and time in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat()

    @registry.register
    def calculate_days_until(target_date: str) -> str:
        """Calculate the number of days from now until a target date (YYYY-MM-DD).

        Args:
            target_date: Date in YYYY-MM-DD format.

        Returns:
            A string like '42 days'.
        """
        target = datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        delta = target - datetime.now(timezone.utc)
        return f"{delta.days} days"

    # ── 2. Create an MCP tool and add it to the same registry ───
    mcp = create_mcp_tool(
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        server_label="github-rest-specs",
        approval_mode="never",
    )
    registry.add_mcp_tool(mcp)

    # ── 3. Build a combined ToolSet ─────────────────────────────
    # Contains both FunctionTool (local) + McpTool (remote)
    toolset = registry.build_toolset()

    # ── 4. Create and run the agent ─────────────────────────────
    with manager.temporary_agent(
        name="mcp-plus-functions",
        instructions=(
            "You are a helpful agent. You can check the current date, "
            "calculate dates, and search Azure REST API specifications. "
            "Use the right tool for each task."
        ),
        toolset=toolset,
    ) as agent:
        handler = McpRunHandler(mcp_tools=[mcp])
        result = manager.run_agent(
            agent.id,
            user_message=(
                "What is today's date? Also, summarize the Azure "
                "Container Apps REST API specification."
            ),
            run_handler=handler,
        )

        print("Agent response:")
        print(result)


if __name__ == "__main__":
    main()
