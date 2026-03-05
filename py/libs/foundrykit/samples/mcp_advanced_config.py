"""Example 5: MCP with custom headers and allowed tool filtering.

Demonstrates advanced MCP configuration:
- Custom authentication headers for the MCP server
- Whitelisting specific tools the agent is allowed to call
- Dynamic allow/disallow of tools at runtime

Prerequisites:
    pip install azure-ai-agents>=1.2.0b3 azure-identity --pre

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT  — Your Azure AI Foundry project endpoint URL.
    FOUNDRY_MODEL_DEPLOYMENT_NAME — Model deployment name (default: gpt-4-1).
    MCP_API_KEY — (optional) API key for authenticated MCP server access.
"""

import os

from foundrykit import AgentManager, get_foundry_client, create_mcp_tool
from foundrykit.mcp import McpRunHandler, build_mcp_toolset


def main() -> None:
    client = get_foundry_client()
    manager = AgentManager(client)

    api_key = os.environ.get("MCP_API_KEY", "demo-key-12345")

    # ── Create MCP tool with auth headers + allowed tools ───────
    mcp = create_mcp_tool(
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        server_label="github-rest-specs",
        allowed_tools=["search_azure_rest_api_code"],  # only this tool
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-Custom-Header": "foundrykit-demo",
        },
        approval_mode="never",
    )

    print(f"Allowed tools: {mcp.allowed_tools}")

    # ── Dynamic tool management ─────────────────────────────────
    # Add another tool at runtime
    mcp.allow_tool("get_repository_info")
    print(f"After allow: {mcp.allowed_tools}")

    # Remove a tool at runtime
    mcp.disallow_tool("get_repository_info")
    print(f"After disallow: {mcp.allowed_tools}")

    # Re-add for the actual run
    mcp.allow_tool("get_repository_info")

    # ── Build toolset and run ───────────────────────────────────
    toolset = build_mcp_toolset(mcp)

    with manager.temporary_agent(
        name="mcp-advanced-config",
        instructions=(
            "You are a helpful agent. Use the MCP tools to search "
            "Azure REST API specifications."
        ),
        toolset=toolset,
    ) as agent:
        handler = McpRunHandler(mcp_tools=[mcp])
        result = manager.run_agent(
            agent.id,
            user_message="Search for Container Apps API operations.",
            run_handler=handler,
        )
        print("\nAgent response:")
        print(result)


if __name__ == "__main__":
    main()
