"""Sample 03: Streaming Agent — receive tokens in real time.

Uses ``run_agent_stream()`` to get incremental text deltas as the agent
generates its response.  This is the pattern used by the loan-origination
backend to power SSE streaming in the chat UI.

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT        — Azure AI Foundry project endpoint.
    FOUNDRY_MODEL_DEPLOYMENT_NAME   — Model deployment (default: gpt-4-1).
"""

from foundrykit import AgentManager, get_foundry_client


def main() -> None:
    client = get_foundry_client()
    manager = AgentManager(client)

    with manager.temporary_agent(
        name="streaming-demo",
        instructions=(
            "You are a knowledgeable assistant. Provide detailed, well-structured "
            "answers using markdown formatting."
        ),
    ) as agent:
        print("Streaming agent response:\n")

        for event in manager.run_agent_stream(
            agent.id,
            user_message="Explain the mortgage loan origination process in 5 steps.",
        ):
            if event.event_type == "text_delta":
                print(event.data, end="", flush=True)
            elif event.event_type == "tool_start":
                print("\n[Tools executing...]")
            elif event.event_type == "tool_complete":
                print("[Tools done]")
            elif event.event_type == "error":
                print(f"\n[ERROR: {event.data}]")

        print("\n\nStream complete.")


if __name__ == "__main__":
    main()
