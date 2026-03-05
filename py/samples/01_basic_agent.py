"""Sample 01: Basic Agent — create, run, get response, cleanup.

The simplest possible foundrykit usage: create a temporary agent, send
one message, print the response.  The ``temporary_agent`` context manager
handles cleanup automatically.

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT        — Azure AI Foundry project endpoint.
    FOUNDRY_MODEL_DEPLOYMENT_NAME   — Model deployment (default: gpt-4-1).
"""

from foundrykit import AgentManager, get_foundry_client


def main() -> None:
    # 1. Obtain a FoundryClient (reads env vars automatically)
    client = get_foundry_client()
    manager = AgentManager(client)

    # 2. Create a temporary agent — deleted on context-manager exit
    with manager.temporary_agent(
        name="basic-demo",
        instructions="You are a helpful assistant that answers questions clearly and concisely.",
    ) as agent:
        # 3. Run the agent synchronously and get the full response
        response = manager.run_agent(
            agent.id,
            user_message="What are the three main benefits of using Azure AI Foundry?",
        )

        print("Agent response:")
        print(response)


if __name__ == "__main__":
    main()
