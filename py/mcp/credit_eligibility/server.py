"""MCP Server: credit-eligibility — Credit checks, scores, and eligibility matrix."""

from __future__ import annotations

import asyncio
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("credit-eligibility", instructions="Credit assessment and eligibility checking for Saudi lending.", host="0.0.0.0", port=8012, stateless_http=True)

# Credit scores by profile
CREDIT_SCORES = {
    "KYC-001": {"score": 742, "rating": "Excellent", "provider": "SIMAH"},
    "KYC-002": {"score": 680, "rating": "Good", "provider": "SIMAH"},
    "KYC-003": {"score": 520, "rating": "Fair", "provider": "SIMAH"},
}

# Eligibility matrix: rating × product type
ELIGIBILITY_MATRIX = {
    ("Excellent", "Murabaha"): {"eligible": True, "max_amount": 500000, "rate": 3.75},
    ("Excellent", "Ijara"): {"eligible": True, "max_amount": 300000, "rate": 3.90},
    ("Excellent", "Tawarruq"): {"eligible": True, "max_amount": 250000, "rate": 4.25},
    ("Good", "Murabaha"): {"eligible": True, "max_amount": 350000, "rate": 4.50},
    ("Good", "Ijara"): {"eligible": True, "max_amount": 200000, "rate": 4.75},
    ("Good", "Tawarruq"): {"eligible": True, "max_amount": 180000, "rate": 5.00},
    ("Fair", "Murabaha"): {"eligible": False, "reason": "Credit score below minimum threshold for Murabaha financing."},
    ("Fair", "Ijara"): {"eligible": False, "reason": "Credit score below minimum threshold for Ijara financing."},
    ("Fair", "Tawarruq"): {"eligible": True, "max_amount": 80000, "rate": 6.50},
}


@mcp.tool()
async def run_credit_check(customer_id: str) -> str:
    """Run a full credit check with 4 animated verification steps. Returns step-by-step progress.

    Args:
        customer_id: The verified customer ID.
    """
    steps = [
        {"step": 1, "label": "Verifying identity with SIMAH", "status": "done", "duration_ms": 800},
        {"step": 2, "label": "Checking credit bureau records", "status": "done", "duration_ms": 900},
        {"step": 3, "label": "Analyzing income & obligations", "status": "done", "duration_ms": 850},
        {"step": 4, "label": "Calculating risk assessment", "status": "done", "duration_ms": 700},
    ]
    await asyncio.sleep(0.5)
    score_data = CREDIT_SCORES.get(customer_id, CREDIT_SCORES["KYC-001"])
    return json.dumps({
        "check_id": f"CC-{customer_id}",
        "steps": steps,
        "result": "completed",
        "score": score_data["score"],
        "rating": score_data["rating"],
    })


@mcp.tool()
async def get_credit_score(customer_id: str) -> str:
    """Get the SIMAH credit score for a customer.

    Args:
        customer_id: The verified customer ID.
    """
    data = CREDIT_SCORES.get(customer_id, CREDIT_SCORES["KYC-001"])
    return json.dumps({
        "customer_id": customer_id,
        **data,
        "score_range": {"min": 300, "max": 900},
    })


@mcp.tool()
async def check_eligibility(customer_id: str, product_type: str, requested_amount: int) -> str:
    """Check if a customer is eligible for a specific product and amount.

    Args:
        customer_id: The verified customer ID.
        product_type: Product type (Murabaha, Ijara, or Tawarruq).
        requested_amount: The requested financing amount in SAR.
    """
    score_data = CREDIT_SCORES.get(customer_id, CREDIT_SCORES["KYC-001"])
    rating = score_data["rating"]
    key = (rating, product_type)
    eligibility = ELIGIBILITY_MATRIX.get(key)

    if not eligibility:
        return json.dumps({"eligible": False, "reason": "Product type not recognized."})

    if not eligibility.get("eligible"):
        return json.dumps({
            "eligible": False,
            "rating": rating,
            "score": score_data["score"],
            "reason": eligibility.get("reason", "Not eligible."),
        })

    max_amt = eligibility["max_amount"]
    approved_amount = min(requested_amount, max_amt)
    return json.dumps({
        "eligible": True,
        "rating": rating,
        "score": score_data["score"],
        "approved_amount": approved_amount,
        "max_amount": max_amt,
        "rate": eligibility["rate"],
        "capped": requested_amount > max_amt,
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
