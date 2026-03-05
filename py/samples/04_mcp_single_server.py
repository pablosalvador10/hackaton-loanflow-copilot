"""Sample 04: Single MCP Server — connect and auto-approve tool calls.

Demonstrates the basic MCP (Model Context Protocol) pattern: connect to a
remote MCP server so the agent can call server-side tools.  Uses
``McpRunHandler`` for automatic tool-call approval.

MCP tools are server-side — the Azure Agent Service calls the remote
server directly.  No local function execution is needed.

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT        — Azure AI Foundry project endpoint.
    FOUNDRY_MODEL_DEPLOYMENT_NAME   — Model deployment (default: gpt-4-1).
"""

from foundrykit import AgentManager, get_foundry_client, create_mcp_tool
from foundrykit.mcp import McpRunHandler, build_mcp_toolset


def main() -> None:
    client = get_foundry_client()
    manager = AgentManager(client)

    # ── 1. Create an MCP tool pointing to a remote server ───────
    mcp = create_mcp_tool(
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        server_label="github-rest-specs",
        approval_mode="never",  # auto-approve all tool calls
    )

    # ── 2. Build a ToolSet containing the MCP tool ──────────────
    toolset = build_mcp_toolset(mcp)

    # ── 3. Create the agent and run it ──────────────────────────
    with manager.temporary_agent(
        name="mcp-single-demo",
        instructions=(
            "You are a helpful agent that can search Azure REST API specs. "
            "Use the available MCP tools to answer questions."
        ),
        toolset=toolset,
    ) as agent:
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
