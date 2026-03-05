"""Example 1: Single MCP Server — basic setup.

Connects to a single remote MCP server (GitMCP for Azure REST API specs)
and runs a simple query.  Auto-approves all MCP tool calls.

Prerequisites:
    pip install azure-ai-agents>=1.2.0b3 azure-identity --pre

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT  — Your Azure AI Foundry project endpoint URL.
    FOUNDRY_MODEL_DEPLOYMENT_NAME — Model deployment name (default: gpt-4-1).
"""

from foundrykit import AgentManager, get_foundry_client, create_mcp_tool
from foundrykit.mcp import McpRunHandler, build_mcp_toolset


def main() -> None:
    # ── 1. Create the foundry client ────────────────────────────
    client = get_foundry_client()
    manager = AgentManager(client)

    # ── 2. Create an MCP tool pointing to a remote server ───────
    mcp = create_mcp_tool(
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        server_label="github-rest-specs",
        approval_mode="never",  # auto-approve all tool calls
    )

    # ── 3. Build a ToolSet containing the MCP tool ──────────────
    toolset = build_mcp_toolset(mcp)

    # ── 4. Create the agent ─────────────────────────────────────
    with manager.temporary_agent(
        name="mcp-demo-single",
        instructions=(
            "You are a helpful agent that can search Azure REST API specs. "
            "Use the available MCP tools to answer questions."
        ),
        toolset=toolset,
    ) as agent:
        # ── 5. Run the agent with MCP handler ───────────────────
        handler = McpRunHandler(mcp_tools=[mcp])
        result = manager.run_agent(
            agent.id,
            user_message="Summarize the Azure Container Apps REST API spec.",
            run_handler=handler,
        )
        print("Agent response:")
        print(result)


if __name__ == "__main__":
    main()
