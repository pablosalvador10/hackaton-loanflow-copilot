"""MCP Server: product-catalog — Loan products, details, and intent matching."""

from __future__ import annotations

import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("product-catalog", instructions="Sharia-compliant loan product catalog for Saudi lending.", host="0.0.0.0", port=8011, stateless_http=True)

PRODUCTS = [
    {
        "product_id": "PROD-MURABAHA-AUTO",
        "name": "Murabaha Auto Financing",
        "icon": "🚗",
        "type": "Murabaha",
        "description": "Cost-plus financing for vehicle purchase. Bank buys the car and sells to you at an agreed profit margin.",
        "max_amount": 500000,
        "max_tenure_months": 60,
        "min_rate": 3.5,
        "badge": "Recommended",
        "sharia_structure": "Murabaha (cost-plus sale)",
        "intents": ["car", "auto", "vehicle", "buy a car"],
    },
    {
        "product_id": "PROD-IJARA-LEASE",
        "name": "Ijara Lease-to-Own",
        "icon": "🏠",
        "type": "Ijara",
        "description": "Lease-to-own arrangement. Bank purchases and leases the asset to you with option to own at end of term.",
        "max_amount": 300000,
        "max_tenure_months": 48,
        "min_rate": 4.0,
        "badge": "Popular",
        "sharia_structure": "Ijara (lease-to-own)",
        "intents": ["home", "renovation", "house", "home renovation"],
    },
    {
        "product_id": "PROD-TAWARRUQ-PERSONAL",
        "name": "Tawarruq Personal Finance",
        "icon": "💰",
        "type": "Tawarruq",
        "description": "Commodity-based personal financing. Get cash deposited directly to your account through commodity trading.",
        "max_amount": 250000,
        "max_tenure_months": 60,
        "min_rate": 4.5,
        "badge": None,
        "sharia_structure": "Tawarruq (commodity murabaha)",
        "intents": ["personal", "cash", "personal loan", "something else"],
    },
    {
        "product_id": "PROD-MURABAHA-GENERAL",
        "name": "Murabaha General Purpose",
        "icon": "📋",
        "type": "Murabaha",
        "description": "General-purpose Sharia-compliant financing for various needs including education, medical, and travel.",
        "max_amount": 200000,
        "max_tenure_months": 48,
        "min_rate": 4.2,
        "badge": None,
        "sharia_structure": "Murabaha (cost-plus sale)",
        "intents": ["general", "education", "medical", "travel", "other"],
    },
]


@mcp.tool()
async def list_loan_products(intent: str | None = None) -> str:
    """List available Sharia-compliant loan products, optionally sorted by user intent.

    Args:
        intent: Optional user intent string (e.g. 'buy a car', 'personal loan', 'home renovation', 'something else').
    """
    products = list(PRODUCTS)
    if intent:
        intent_lower = intent.lower()
        def score(p: dict) -> int:
            return sum(1 for i in p["intents"] if i in intent_lower) * -1
        products.sort(key=score)
    return json.dumps([{k: v for k, v in p.items() if k != "intents"} for p in products])


@mcp.tool()
async def get_product_details(product_id: str) -> str:
    """Get detailed information about a specific loan product.

    Args:
        product_id: The product identifier (e.g. PROD-MURABAHA-AUTO).
    """
    for p in PRODUCTS:
        if p["product_id"] == product_id:
            return json.dumps({k: v for k, v in p.items() if k != "intents"})
    return json.dumps({"error": "Product not found"})


@mcp.tool()
async def get_product_by_intent(user_message: str) -> str:
    """Find the best matching product based on the user's natural language message.

    Args:
        user_message: The user's message describing what they need.
    """
    msg = user_message.lower()
    for p in PRODUCTS:
        for intent in p["intents"]:
            if intent in msg:
                return json.dumps({k: v for k, v in p.items() if k != "intents"})
    # Default to Tawarruq for unmatched
    return json.dumps({k: v for k, v in PRODUCTS[2].items() if k != "intents"})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
