"""MCP Server: offers-pricing — Offer generation, payment calculation, adjustments."""

from __future__ import annotations

import json
import math
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("offers-pricing", instructions="Offer generation and pricing tools for Saudi lending.", host="0.0.0.0", port=8013)


def _calc_monthly(principal: int, annual_rate: float, tenure_months: int) -> float:
    """Simple amortization monthly payment."""
    if annual_rate == 0:
        return principal / tenure_months
    r = annual_rate / 100 / 12
    return principal * r * math.pow(1 + r, tenure_months) / (math.pow(1 + r, tenure_months) - 1)


@mcp.tool()
async def generate_offer(
    customer_id: str,
    product_id: str,
    product_type: str,
    amount: int,
    rate: float,
    tenure_months: int = 60,
) -> str:
    """Generate a personalized financing offer with monthly payment details.

    Args:
        customer_id: The verified customer ID.
        product_id: The selected product ID.
        product_type: Product type (Murabaha, Ijara, Tawarruq).
        amount: Approved financing amount in SAR.
        rate: Annual profit rate percentage.
        tenure_months: Loan tenure in months (default 60).
    """
    monthly = round(_calc_monthly(amount, rate, tenure_months))
    total_cost = monthly * tenure_months
    bank_profit = total_cost - amount

    return json.dumps({
        "offer_id": f"OFF-{customer_id}-{product_id[-4:]}",
        "customer_id": customer_id,
        "product_id": product_id,
        "product_type": product_type,
        "amount": amount,
        "monthly_payment": monthly,
        "tenure_months": tenure_months,
        "annual_rate": rate,
        "total_cost": total_cost,
        "bank_profit": bank_profit,
        "sharia_compliant": True,
        "status": "pre_approved",
    })


@mcp.tool()
async def calculate_monthly_payment(amount: int, rate: float, tenure_months: int) -> str:
    """Calculate monthly payment for given amount, rate, and tenure (slider use case).

    Args:
        amount: Financing amount in SAR.
        rate: Annual profit rate percentage.
        tenure_months: Loan tenure in months.
    """
    monthly = round(_calc_monthly(amount, rate, tenure_months))
    return json.dumps({
        "amount": amount,
        "rate": rate,
        "tenure_months": tenure_months,
        "monthly_payment": monthly,
        "total_cost": monthly * tenure_months,
    })


@mcp.tool()
async def adjust_offer(offer_id: str, new_amount: int | None = None, new_tenure: int | None = None) -> str:
    """Adjust an existing offer's amount or tenure and recalculate.

    Args:
        offer_id: The existing offer ID.
        new_amount: New financing amount in SAR (optional).
        new_tenure: New tenure in months (optional).
    """
    # Simulate adjustment with defaults
    amount = new_amount or 150000
    tenure = new_tenure or 60
    rate = 3.75
    monthly = round(_calc_monthly(amount, rate, tenure))
    total_cost = monthly * tenure

    return json.dumps({
        "offer_id": offer_id,
        "adjusted": True,
        "amount": amount,
        "monthly_payment": monthly,
        "tenure_months": tenure,
        "annual_rate": rate,
        "total_cost": total_cost,
        "status": "pre_approved",
    })


@mcp.tool()
async def decline_offer(offer_id: str, reason: str | None = None) -> str:
    """Record that the customer declined or wants to think about the offer.

    Args:
        offer_id: The offer ID being declined.
        reason: Optional reason for declining.
    """
    return json.dumps({
        "offer_id": offer_id,
        "status": "declined",
        "reason": reason or "Customer needs more time to decide.",
        "follow_up": "We'll keep this offer available for 7 days. You can return anytime.",
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
