"""Example 4: Streaming with MCP tools.

Demonstrates using ``run_agent_stream()`` with MCP tools so you can
receive text deltas in real time while MCP tool calls are auto-approved
in the background.

Prerequisites:
    pip install azure-ai-agents>=1.2.0b3 azure-identity --pre

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT  — Your Azure AI Foundry project endpoint URL.
    FOUNDRY_MODEL_DEPLOYMENT_NAME — Model deployment name (default: gpt-4-1).
"""

from foundrykit import AgentManager, get_foundry_client, create_mcp_tool
from foundrykit.mcp import build_mcp_toolset


def main() -> None:
    client = get_foundry_client()
    manager = AgentManager(client)

    # ── Create MCP tool ─────────────────────────────────────────
    mcp = create_mcp_tool(
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        server_label="github-rest-specs",
        approval_mode="never",
    )

    toolset = build_mcp_toolset(mcp)

    # ── Create agent ────────────────────────────────────────────
    with manager.temporary_agent(
        name="mcp-streaming-demo",
        instructions=(
            "You are a helpful agent that can search Azure REST API specs. "
            "Use the available MCP tools to answer questions."
        ),
        toolset=toolset,
    ) as agent:
        # ── Stream the response ─────────────────────────────────
        # Pass mcp_tools so the stream handler can auto-approve
        print("Streaming agent response:\n")
        for event in manager.run_agent_stream(
            agent.id,
            user_message="List the main resource types in the Azure Container Apps API.",
            mcp_tools=[mcp],
        ):
            if event.event_type == "text_delta":
                print(event.data, end="", flush=True)
            elif event.event_type == "mcp_approved":
                print(f"\n[MCP tool approved: {event.metadata.get('tool_call_id')}]")
            elif event.event_type == "tool_start":
                print("\n[Tools executing...]")
            elif event.event_type == "tool_complete":
                print("[Tools complete]")
            elif event.event_type == "error":
                print(f"\n[ERROR: {event.data}]")

        print("\n\nStream complete.")


if __name__ == "__main__":
    main()
