"""Example 3: MCP tools + local function tools in the same agent.

Demonstrates combining remote MCP tools (server-side) with local Python
function tools (client-side) in a single ``ToolRegistry`` / ``ToolSet``.

The agent gets:
- MCP access to Azure REST API specs (remote / server-side)
- A local ``get_current_date`` function (client-side, auto-executed)

Prerequisites:
    pip install azure-ai-agents>=1.2.0b3 azure-identity --pre

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT  — Your Azure AI Foundry project endpoint URL.
    FOUNDRY_MODEL_DEPLOYMENT_NAME — Model deployment name (default: gpt-4-1).
"""

from datetime import datetime, timezone

from foundrykit import AgentManager, ToolRegistry, get_foundry_client, create_mcp_tool
from foundrykit.mcp import McpRunHandler


def main() -> None:
    client = get_foundry_client()
    manager = AgentManager(client)

    # ── 1. Create a ToolRegistry with local functions ───────────
    registry = ToolRegistry()

    @registry.register
    def get_current_date() -> str:
        """Return the current date and time in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat()

    @registry.register
    def calculate_days_until(target_date: str) -> str:
        """Calculate the number of days until a target date (YYYY-MM-DD)."""
        target = datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        delta = target - datetime.now(timezone.utc)
        return f"{delta.days} days"

    # ── 2. Create an MCP tool ───────────────────────────────────
    mcp = create_mcp_tool(
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        server_label="github-rest-specs",
        approval_mode="never",
    )

    # ── 3. Add the MCP tool to the same registry ────────────────
    registry.add_mcp_tool(mcp)

    # ── 4. Build a combined ToolSet ─────────────────────────────
    # The toolset now contains both FunctionTool (local) + McpTool (remote)
    toolset = registry.build_toolset()

    # ── 5. Create and run the agent ─────────────────────────────
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
