"""Sample 02: Agent with local function tools.

Shows how to use ``ToolRegistry`` to register plain Python functions as
agent tools.  The Foundry agent can decide to call these tools during
its reasoning loop.  Tool execution happens locally and is instrumented
with OpenTelemetry spans automatically.

Important: tool functions MUST be synchronous and return ``str``.

Environment variables:
    FOUNDRY_PROJECT_ENDPOINT        — Azure AI Foundry project endpoint.
    FOUNDRY_MODEL_DEPLOYMENT_NAME   — Model deployment (default: gpt-4-1).
"""

import json
from datetime import datetime, timezone

from foundrykit import AgentManager, ToolRegistry, get_foundry_client


def main() -> None:
    client = get_foundry_client()
    manager = AgentManager(client)

    # ── 1. Create a ToolRegistry and register functions ─────────
    registry = ToolRegistry()

    @registry.register
    def get_current_date() -> str:
        """Return the current UTC date and time in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat()

    @registry.register
    def calculate_monthly_payment(
        principal: float,
        annual_rate: float,
        term_months: int,
    ) -> str:
        """Calculate a fixed monthly loan payment.

        Args:
            principal: Loan amount in dollars.
            annual_rate: Annual interest rate as a percentage (e.g. 6.5).
            term_months: Loan term in months (e.g. 360 for 30 years).

        Returns:
            JSON string with the monthly payment amount.
        """
        monthly_rate = (annual_rate / 100) / 12
        if monthly_rate == 0:
            payment = principal / term_months
        else:
            payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / (
                (1 + monthly_rate) ** term_months - 1
            )
        return json.dumps({"monthly_payment": round(payment, 2)})

    # ── 2. Build the toolset ────────────────────────────────────
    toolset = registry.build_toolset()

    # ── 3. Create and run the agent ─────────────────────────────
    with manager.temporary_agent(
        name="tool-demo",
        instructions=(
            "You are a helpful financial assistant. Use the available tools "
            "to answer questions about dates and loan payments. Always show "
            "the calculation details."
        ),
        toolset=toolset,
    ) as agent:
        response = manager.run_agent(
            agent.id,
            user_message=(
                "What is today's date? Also, what would the monthly payment be "
                "on a $400,000 mortgage at 6.5% for 30 years?"
            ),
        )

        print("Agent response:")
        print(response)


if __name__ == "__main__":
    main()
