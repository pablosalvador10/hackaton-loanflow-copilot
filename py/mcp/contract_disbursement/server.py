"""MCP Server: contract-disbursement — Contract creation, OTP, disbursement, status."""

from __future__ import annotations

import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("contract-disbursement", instructions="Contract signing and fund disbursement for Saudi lending.", host="0.0.0.0", port=8014)

# Contract summaries by product type
CONTRACT_TEMPLATES = {
    "Murabaha": {
        "contract_type": "Murabaha Sale",
        "description": "Sharia-compliant sale agreement where the bank purchases the asset and sells it to you at an agreed markup.",
        "insurance": "Included",
    },
    "Ijara": {
        "contract_type": "Ijara Lease-to-Own",
        "description": "Sharia-compliant lease agreement where the bank purchases and leases the asset with transfer of ownership at end of term.",
        "insurance": "Included",
    },
    "Tawarruq": {
        "contract_type": "Tawarruq Commodity",
        "description": "Sharia-compliant commodity-based financing where funds are deposited directly to your account through commodity trading.",
        "insurance": "Optional",
    },
}

VALID_OTP = "7249"


@mcp.tool()
async def create_contract(
    offer_id: str,
    customer_id: str,
    product_type: str,
    amount: int,
    monthly_payment: int,
    tenure_months: int,
    rate: float,
) -> str:
    """Create a contract summary for the accepted offer.

    Args:
        offer_id: The accepted offer ID.
        customer_id: The customer ID.
        product_type: Product type (Murabaha, Ijara, Tawarruq).
        amount: Financing amount in SAR.
        monthly_payment: Monthly payment in SAR.
        tenure_months: Tenure in months.
        rate: Annual profit rate.
    """
    template = CONTRACT_TEMPLATES.get(product_type, CONTRACT_TEMPLATES["Murabaha"])
    total_cost = monthly_payment * tenure_months
    bank_profit = total_cost - amount

    return json.dumps({
        "contract_id": f"CTR-{offer_id}",
        "offer_id": offer_id,
        "customer_id": customer_id,
        "contract_type": template["contract_type"],
        "description": template["description"],
        "purchase_price": amount,
        "bank_profit": bank_profit,
        "total_sale_price": total_cost,
        "installments": f"{tenure_months} x SAR {monthly_payment:,}",
        "insurance": template["insurance"],
        "status": "pending_signature",
        "otp_sent": True,
        "otp_message": "Verification code sent to registered mobile number.",
    })


@mcp.tool()
async def verify_otp(contract_id: str, otp_code: str) -> str:
    """Verify OTP to digitally sign the contract. Only '7249' is valid.

    Args:
        contract_id: The contract ID.
        otp_code: The OTP code entered by the customer.
    """
    # Strip spaces for flexibility
    clean_otp = otp_code.replace(" ", "")
    if clean_otp == VALID_OTP:
        return json.dumps({
            "contract_id": contract_id,
            "otp_valid": True,
            "status": "signed",
            "message": "Contract signed successfully!",
        })
    return json.dumps({
        "contract_id": contract_id,
        "otp_valid": False,
        "status": "pending_signature",
        "message": "Invalid OTP. Please try again.",
        "attempts_remaining": 2,
    })


@mcp.tool()
async def disburse_funds(contract_id: str, customer_id: str, amount: int) -> str:
    """Process fund disbursement via SADAD after contract signing.

    Args:
        contract_id: The signed contract ID.
        customer_id: The customer ID.
        amount: The disbursement amount in SAR.
    """
    return json.dumps({
        "disbursement_id": f"DSB-{contract_id}",
        "contract_id": contract_id,
        "customer_id": customer_id,
        "amount": amount,
        "method": "SADAD",
        "account_ending": "4821",
        "status": "completed",
        "reference": f"SADAD-{contract_id[-6:]}",
        "celebration": {
            "title": "Congratulations!",
            "message": "Your financing has been approved and funds are being transferred to your account.",
            "amount": amount,
            "account_hint": "•••4821",
        },
    })


@mcp.tool()
async def get_contract_status(contract_id: str) -> str:
    """Get the current status of a contract.

    Args:
        contract_id: The contract ID to check.
    """
    return json.dumps({
        "contract_id": contract_id,
        "status": "active",
        "disbursed": True,
        "next_payment_date": "2026-04-05",
        "payments_made": 0,
        "payments_remaining": 60,
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
