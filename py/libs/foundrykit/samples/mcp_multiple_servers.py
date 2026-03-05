"""Example 2: Multiple MCP Servers.

Connects to TWO remote MCP servers simultaneously:
- GitMCP for Azure REST API specs
- Microsoft Learn documentation

The agent can draw from both sources to answer questions.

Prerequisites:
    pip install azure-ai-agents>=1.2.0b3 azure-identity --pre

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT  — Your Azure AI Foundry project endpoint URL.
    FOUNDRY_MODEL_DEPLOYMENT_NAME — Model deployment name (default: gpt-4-1).
"""

from foundrykit import AgentManager, get_foundry_client, create_mcp_tool
from foundrykit.mcp import McpRunHandler, build_mcp_toolset


def main() -> None:
    client = get_foundry_client()
    manager = AgentManager(client)

    # ── Create two MCP tools for different servers ──────────────
    github_mcp = create_mcp_tool(
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        server_label="github-rest-specs",
        approval_mode="never",
    )

    mslearn_mcp = create_mcp_tool(
        server_url="https://learn.microsoft.com/api/mcp",
        server_label="microsoft-learn",
        allowed_tools=["microsoft_docs_search"],  # whitelist specific tools
        approval_mode="never",
    )

    # ── Build a single ToolSet with both MCPs ───────────────────
    toolset = build_mcp_toolset(github_mcp, mslearn_mcp)

    # ── Create the agent ────────────────────────────────────────
    with manager.temporary_agent(
        name="mcp-demo-multi",
        instructions=(
            "You are a helpful agent with access to Azure REST API specs "
            "and Microsoft Learn documentation. Use both sources to give "
            "comprehensive answers."
        ),
        toolset=toolset,
    ) as agent:
        # ── Run — the handler auto-approves calls to both MCPs ──
        handler = McpRunHandler(mcp_tools=[github_mcp, mslearn_mcp])
        result = manager.run_agent(
            agent.id,
            user_message=(
                "What are the CLI commands to create an Azure Container App "
                "with a managed identity? Cross-reference the REST API spec."
            ),
            run_handler=handler,
        )
        print("Agent response:")
        print(result)


if __name__ == "__main__":
    main()
