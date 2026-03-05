"""MCP Server: identity-kyc — Nafath verification, National ID, customer profiles."""

from __future__ import annotations

import asyncio
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("identity-kyc", instructions="Identity verification and KYC tools for Saudi lending.", host="0.0.0.0", port=8010, stateless_http=True)

# Mock customer profiles
PROFILES = {
    "mohammed": {
        "customer_id": "KYC-001",
        "national_id": "1088******",
        "full_name": "Mohammed Al-Salem",
        "employer": "Saudi Aramco",
        "monthly_salary": 28500,
        "employment_years": 8,
        "credit_rating": "Excellent",
        "age": 34,
        "dependents": 2,
        "existing_obligations": 3200,
    },
    "fatima": {
        "customer_id": "KYC-002",
        "national_id": "1092******",
        "full_name": "Fatima Al-Rashid",
        "employer": "SABIC",
        "monthly_salary": 22000,
        "employment_years": 5,
        "credit_rating": "Good",
        "age": 29,
        "dependents": 0,
        "existing_obligations": 1800,
    },
    "ahmad": {
        "customer_id": "KYC-003",
        "national_id": "1075******",
        "full_name": "Ahmad Al-Dosari",
        "employer": "Private Business",
        "monthly_salary": 15000,
        "employment_years": 2,
        "credit_rating": "Fair",
        "age": 42,
        "dependents": 4,
        "existing_obligations": 6500,
    },
}


@mcp.tool()
async def verify_nafath(national_id: str) -> str:
    """Initiate Nafath identity verification. Returns a verification code the user must confirm in their Nafath app.

    Args:
        national_id: The customer's national ID number.
    """
    await asyncio.sleep(0.5)  # simulate network
    return json.dumps({
        "status": "pending",
        "verification_code": 47,
        "message": "Please approve code 47 in your Nafath app.",
        "session_id": f"nafath-{national_id[-4:]}",
        "expires_in_seconds": 120,
    })


@mcp.tool()
async def verify_national_id(national_id: str, full_name: str, date_of_birth: str) -> str:
    """Manual identity verification using National ID details (alternative to Nafath).

    Args:
        national_id: The customer's national ID number.
        full_name: Full name as on the ID.
        date_of_birth: Date of birth in YYYY-MM-DD format.
    """
    await asyncio.sleep(0.3)
    # Match against mock profiles
    for profile in PROFILES.values():
        if national_id.startswith(profile["national_id"][:4]):
            return json.dumps({
                "status": "verified",
                "customer_id": profile["customer_id"],
                "full_name": profile["full_name"],
                "national_id": profile["national_id"],
                "verification_method": "manual",
            })
    return json.dumps({"status": "failed", "message": "National ID not found in records."})


@mcp.tool()
async def get_customer_profile(customer_id: str) -> str:
    """Retrieve full customer profile after identity verification.

    Args:
        customer_id: The verified customer ID (e.g. KYC-001).
    """
    for profile in PROFILES.values():
        if profile["customer_id"] == customer_id:
            return json.dumps(profile)
    # Default to Mohammed for demo
    return json.dumps(PROFILES["mohammed"])


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
