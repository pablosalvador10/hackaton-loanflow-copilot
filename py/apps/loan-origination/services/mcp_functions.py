"""Local MCP function wrappers for the loan origination agent.

Instead of Foundry's cloud-side MCP connector (which cannot reach localhost
URLs), each MCP tool is exposed as a regular Python ``FunctionTool``.

The Azure AI Agents SDK executes these functions locally (same process as the
FastAPI backend) and submits their results back to the Foundry agent, so all
network calls to the MCP servers go through ``localhost`` where they are
reachable.

Usage in the loan router::

    from services.mcp_functions import register_mcp_functions

    registry = ToolRegistry()
    register_mcp_functions(registry)
    toolset = registry.build_toolset()
"""

from __future__ import annotations

import json
import threading
from typing import Optional

import httpx
import structlog
from opentelemetry import trace

from core.config import settings

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


# ── Thread-local tool results store ─────────────────────────────
# Each agent run clears the store before starting, then key tool
# functions write their parsed results here.  After the run, loan.py
# reads the store to determine which rich card to emit to the frontend.

_tl = threading.local()


def clear_tool_results() -> None:
    """Reset the thread-local store before a new agent run."""
    _tl.results = {}


def _store_result(tool_name: str, raw: str) -> None:
    """Parse and cache a tool result in thread-local storage."""
    store: dict | None = getattr(_tl, "results", None)
    if store is None:
        return
    try:
        store[tool_name] = json.loads(raw)
    except Exception:
        store[tool_name] = raw


def get_tool_results() -> dict:
    """Return a snapshot of tool results collected during the current run."""
    return dict(getattr(_tl, "results", {}))


# ── MCP HTTP helper ──────────────────────────────────────────────


def _call_mcp(server_url: str, tool_name: str, arguments: dict) -> str:
    """POST a ``tools/call`` JSON-RPC request to a local MCP server.

    :param server_url: Full URL to the MCP endpoint (e.g. ``http://localhost:8010/mcp``).
    :param tool_name: Name of the MCP tool to invoke.
    :param arguments: Dict of keyword arguments for the tool.
    :return: Plain-text result from the tool, or an error description.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                server_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            resp.raise_for_status()

        # MCP (stateless-HTTP) responses are SSE lines: "data: {...}"
        for line in resp.text.splitlines():
            if line.startswith("data: "):
                obj = json.loads(line[6:])
                result = obj.get("result", {})
                if "content" in result:
                    parts = [
                        c.get("text", "")
                        for c in result["content"]
                        if c.get("type") == "text"
                    ]
                    return "\n".join(parts)
                return json.dumps(result)

        return resp.text

    except Exception as exc:
        logger.exception("mcp_call_failed", tool=tool_name, error=str(exc))
        return f"Error calling {tool_name}: {exc}"


# ── Identity / KYC tools (port 8010) ────────────────────────────


def verify_nafath(national_id: str) -> str:
    """Initiate Nafath identity verification. Returns a verification code the user must confirm in their Nafath app.

    :param national_id: The customer's national ID number.
    :return: JSON string with the verification result.
    """
    with tracer.start_as_current_span("mcp.verify_nafath") as span:
        span.set_attribute("tool.name", "verify_nafath")
        span.set_attribute("tool.national_id", national_id)
        result = _call_mcp(settings.mcp_identity_url, "verify_nafath", {"national_id": national_id})
        _store_result("verify_nafath", result)
        return result


def verify_national_id(national_id: str, full_name: str, date_of_birth: str) -> str:
    """Manual identity verification using National ID details (alternative to Nafath).

    :param national_id: The customer's national ID number.
    :param full_name: Full name as on the ID.
    :param date_of_birth: Date of birth in YYYY-MM-DD format.
    :return: JSON string with the verification result.
    """
    with tracer.start_as_current_span("mcp.verify_national_id") as span:
        span.set_attribute("tool.name", "verify_national_id")
        result = _call_mcp(
            settings.mcp_identity_url,
            "verify_national_id",
            {"national_id": national_id, "full_name": full_name, "date_of_birth": date_of_birth},
        )
        _store_result("verify_national_id", result)
        return result


def get_customer_profile(customer_id: str) -> str:
    """Retrieve full customer profile after identity verification.

    :param customer_id: The verified customer ID (e.g. KYC-001).
    :return: JSON string with the full customer profile.
    """
    with tracer.start_as_current_span("mcp.get_customer_profile") as span:
        span.set_attribute("tool.name", "get_customer_profile")
        span.set_attribute("tool.customer_id", customer_id)
        result = _call_mcp(
            settings.mcp_identity_url, "get_customer_profile", {"customer_id": customer_id}
        )
        _store_result("get_customer_profile", result)
        return result


# ── Product catalog tools (port 8011) ───────────────────────────


def list_loan_products(intent: Optional[str] = None) -> str:
    """List available Sharia-compliant loan products, optionally sorted by user intent.

    :param intent: Optional natural-language intent (e.g. 'car', 'home').
    :return: JSON string listing all matching products.
    """
    with tracer.start_as_current_span("mcp.list_loan_products") as span:
        span.set_attribute("tool.name", "list_loan_products")
        args: dict = {}
        if intent:
            args["intent"] = intent
        result = _call_mcp(settings.mcp_product_url, "list_loan_products", args)
        _store_result("list_loan_products", result)
        return result


def get_product_details(product_id: str) -> str:
    """Get detailed information about a specific loan product.

    :param product_id: The product ID to look up.
    :return: JSON string with full product details.
    """
    with tracer.start_as_current_span("mcp.get_product_details") as span:
        span.set_attribute("tool.name", "get_product_details")
        return _call_mcp(
            settings.mcp_product_url, "get_product_details", {"product_id": product_id}
        )


def get_product_by_intent(user_message: str) -> str:
    """Find the best matching loan product based on the user's natural language message.

    :param user_message: The user's natural language request describing financing needs.
    :return: JSON string with the best matching product.
    """
    with tracer.start_as_current_span("mcp.get_product_by_intent") as span:
        span.set_attribute("tool.name", "get_product_by_intent")
        result = _call_mcp(
            settings.mcp_product_url, "get_product_by_intent", {"user_message": user_message}
        )
        _store_result("get_product_by_intent", result)
        return result


# ── Credit eligibility tools (port 8012) ────────────────────────


def run_credit_check(customer_id: str) -> str:
    """Run a full credit check with animated verification steps. Returns step-by-step progress.

    :param customer_id: The verified customer ID.
    :return: JSON string with credit check results.
    """
    with tracer.start_as_current_span("mcp.run_credit_check") as span:
        span.set_attribute("tool.name", "run_credit_check")
        span.set_attribute("tool.customer_id", customer_id)
        result = _call_mcp(
            settings.mcp_credit_url, "run_credit_check", {"customer_id": customer_id}
        )
        _store_result("run_credit_check", result)
        return result


def get_credit_score(customer_id: str) -> str:
    """Get the SIMAH credit score for a customer.

    :param customer_id: The verified customer ID.
    :return: JSON string with the credit score.
    """
    with tracer.start_as_current_span("mcp.get_credit_score") as span:
        span.set_attribute("tool.name", "get_credit_score")
        result = _call_mcp(
            settings.mcp_credit_url, "get_credit_score", {"customer_id": customer_id}
        )
        _store_result("get_credit_score", result)
        return result


def check_eligibility(customer_id: str, product_type: str, requested_amount: int) -> str:
    """Check if a customer is eligible for a specific product and amount.

    :param customer_id: The verified customer ID.
    :param product_type: The loan product type (e.g. 'auto', 'personal', 'mortgage').
    :param requested_amount: The requested loan amount in SAR.
    :return: JSON string with eligibility result.
    """
    with tracer.start_as_current_span("mcp.check_eligibility") as span:
        span.set_attribute("tool.name", "check_eligibility")
        result = _call_mcp(
            settings.mcp_credit_url,
            "check_eligibility",
            {
                "customer_id": customer_id,
                "product_type": product_type,
                "requested_amount": requested_amount,
            },
        )
        _store_result("check_eligibility", result)
        return result


# ── Offers & pricing tools (port 8013) ──────────────────────────


def generate_offer(
    customer_id: str,
    product_id: str,
    product_type: str,
    amount: int,
    rate: float,
    tenure_months: int = 60,
) -> str:
    """Generate a personalized financing offer with monthly payment details.

    :param customer_id: The verified customer ID.
    :param product_id: The loan product ID.
    :param product_type: The loan product type (e.g. 'auto', 'personal').
    :param amount: The loan amount in SAR.
    :param rate: The annual profit rate (e.g. 0.0499 for 4.99%).
    :param tenure_months: Loan duration in months (default 60).
    :return: JSON string with the generated offer.
    """
    with tracer.start_as_current_span("mcp.generate_offer") as span:
        span.set_attribute("tool.name", "generate_offer")
        result = _call_mcp(
            settings.mcp_offers_url,
            "generate_offer",
            {
                "customer_id": customer_id,
                "product_id": product_id,
                "product_type": product_type,
                "amount": amount,
                "rate": rate,
                "tenure_months": tenure_months,
            },
        )
        _store_result("generate_offer", result)
        return result


def calculate_monthly_payment(amount: int, rate: float, tenure_months: int) -> str:
    """Calculate monthly payment for given amount, rate, and tenure.

    :param amount: The loan amount in SAR.
    :param rate: The annual profit rate (e.g. 0.0499 for 4.99%).
    :param tenure_months: Loan duration in months.
    :return: JSON string with the calculated monthly payment.
    """
    with tracer.start_as_current_span("mcp.calculate_monthly_payment") as span:
        span.set_attribute("tool.name", "calculate_monthly_payment")
        result = _call_mcp(
            settings.mcp_offers_url,
            "calculate_monthly_payment",
            {"amount": amount, "rate": rate, "tenure_months": tenure_months},
        )
        _store_result("calculate_monthly_payment", result)
        return result


def adjust_offer(
    offer_id: str,
    new_amount: Optional[int] = None,
    new_tenure: Optional[int] = None,
) -> str:
    """Adjust an existing offer's amount or tenure and recalculate.

    :param offer_id: The offer ID to adjust.
    :param new_amount: New loan amount in SAR (optional).
    :param new_tenure: New tenure in months (optional).
    :return: JSON string with the adjusted offer.
    """
    with tracer.start_as_current_span("mcp.adjust_offer") as span:
        span.set_attribute("tool.name", "adjust_offer")
        args: dict = {"offer_id": offer_id}
        if new_amount is not None:
            args["new_amount"] = new_amount
        if new_tenure is not None:
            args["new_tenure"] = new_tenure
        return _call_mcp(settings.mcp_offers_url, "adjust_offer", args)


def decline_offer(offer_id: str, reason: Optional[str] = None) -> str:
    """Record that the customer declined or wants to think about the offer.

    :param offer_id: The offer ID that was declined.
    :param reason: Optional reason for declining.
    :return: JSON string confirming the decline was recorded.
    """
    with tracer.start_as_current_span("mcp.decline_offer") as span:
        span.set_attribute("tool.name", "decline_offer")
        args: dict = {"offer_id": offer_id}
        if reason is not None:
            args["reason"] = reason
        return _call_mcp(settings.mcp_offers_url, "decline_offer", args)


# ── Contract & disbursement tools (port 8014) ────────────────────


def create_contract(
    offer_id: str,
    customer_id: str,
    product_type: str,
    amount: int,
    monthly_payment: int,
    tenure_months: int,
    rate: float,
) -> str:
    """Create a contract summary for an accepted offer.

    :param offer_id: The accepted offer ID.
    :param customer_id: The verified customer ID.
    :param product_type: The loan product type.
    :param amount: The loan amount in SAR.
    :param monthly_payment: The monthly payment in SAR.
    :param tenure_months: The loan duration in months.
    :param rate: The annual profit rate.
    :return: JSON string with the contract details.
    """
    with tracer.start_as_current_span("mcp.create_contract") as span:
        span.set_attribute("tool.name", "create_contract")
        result = _call_mcp(
            settings.mcp_contract_url,
            "create_contract",
            {
                "offer_id": offer_id,
                "customer_id": customer_id,
                "product_type": product_type,
                "amount": amount,
                "monthly_payment": monthly_payment,
                "tenure_months": tenure_months,
                "rate": rate,
            },
        )
        _store_result("create_contract", result)
        return result


def verify_otp(contract_id: str, otp_code: str) -> str:
    """Verify OTP to digitally sign the contract.

    :param contract_id: The contract ID to sign.
    :param otp_code: The 4-digit OTP code entered by the customer.
    :return: JSON string with the OTP verification result.
    """
    with tracer.start_as_current_span("mcp.verify_otp") as span:
        span.set_attribute("tool.name", "verify_otp")
        return _call_mcp(
            settings.mcp_contract_url,
            "verify_otp",
            {"contract_id": contract_id, "otp_code": otp_code},
        )


def disburse_funds(contract_id: str, customer_id: str, amount: int) -> str:
    """Process fund disbursement via SADAD after contract signing.

    :param contract_id: The signed contract ID.
    :param customer_id: The customer ID.
    :param amount: The disbursement amount in SAR.
    :return: JSON string with disbursement confirmation.
    """
    with tracer.start_as_current_span("mcp.disburse_funds") as span:
        span.set_attribute("tool.name", "disburse_funds")
        return _call_mcp(
            settings.mcp_contract_url,
            "disburse_funds",
            {"contract_id": contract_id, "customer_id": customer_id, "amount": amount},
        )


def get_contract_status(contract_id: str) -> str:
    """Get the current status of a contract.

    :param contract_id: The contract ID to check.
    :return: JSON string with the current contract status.
    """
    with tracer.start_as_current_span("mcp.get_contract_status") as span:
        span.set_attribute("tool.name", "get_contract_status")
        return _call_mcp(
            settings.mcp_contract_url,
            "get_contract_status",
            {"contract_id": contract_id},
        )


# ── Registry integration ─────────────────────────────────────────

#: All 16 MCP tool functions in declaration order.
ALL_MCP_FUNCTIONS = [
    # identity_kyc
    verify_nafath,
    verify_national_id,
    get_customer_profile,
    # product_catalog
    list_loan_products,
    get_product_details,
    get_product_by_intent,
    # credit_eligibility
    run_credit_check,
    get_credit_score,
    check_eligibility,
    # offers_pricing
    generate_offer,
    calculate_monthly_payment,
    adjust_offer,
    decline_offer,
    # contract_disbursement
    create_contract,
    verify_otp,
    disburse_funds,
    get_contract_status,
]


def register_mcp_functions(registry) -> int:
    """Register all 16 MCP tool wrappers as local ``FunctionTool`` callables.

    Call this instead of ``registry.add_mcp_tool()`` so that the Azure AI
    Agents SDK executes tool calls locally (hitting ``localhost`` MCP servers)
    rather than via Foundry's cloud-side MCP connector.

    :param registry: A :class:`foundrykit.ToolRegistry` instance.
    :return: Number of functions registered.
    """
    registered = 0
    for fn in ALL_MCP_FUNCTIONS:
        try:
            registry.register(fn)
            registered += 1
            logger.debug("mcp_fn_registered", name=fn.__name__)
        except Exception as exc:
            logger.exception("mcp_fn_register_failed", name=fn.__name__, error=str(exc))

    logger.info("mcp_functions_registered", count=registered)
    return registered
