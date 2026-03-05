"""MCP server configuration for the Loan Origination agent.

Provides MCP tools for:
1. Legacy single MCP server (``MCP_SERVER_URL``)
2. Copilot MCP servers (5 servers for the conversational lending flow)

Usage in the loan router::

    from services.mcp_setup import get_mcp_tool, get_mcp_handler, get_copilot_mcp_tools

    mcp = get_mcp_tool()
    if mcp:
        registry.add_mcp_tool(mcp)

    for tool in get_copilot_mcp_tools():
        registry.add_mcp_tool(tool)
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from foundrykit.mcp import McpRunHandler, create_mcp_tool
from opentelemetry import trace

from core.config import settings

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


@lru_cache(maxsize=1)
def get_mcp_tool():
    """Create the legacy MCP tool if ``MCP_SERVER_URL`` is configured."""
    if not settings.mcp_server_url:
        logger.info("mcp_disabled", reason="MCP_SERVER_URL not configured")
        return None

    with tracer.start_as_current_span("loan.create_mcp_tool") as span:
        span.set_attribute("mcp.server_url", settings.mcp_server_url)
        span.set_attribute("mcp.server_label", settings.mcp_server_label)

        try:
            headers: dict[str, str] = {}
            if settings.mcp_api_key:
                headers["Authorization"] = f"Bearer {settings.mcp_api_key}"

            allowed = (
                [t.strip() for t in settings.mcp_allowed_tools.split(",") if t.strip()]
                if settings.mcp_allowed_tools
                else []
            )

            mcp = create_mcp_tool(
                server_url=settings.mcp_server_url,
                server_label=settings.mcp_server_label,
                allowed_tools=allowed or None,
                headers=headers or None,
                approval_mode=settings.mcp_approval_mode,
            )

            logger.info(
                "mcp_tool_created",
                server_label=settings.mcp_server_label,
                server_url=settings.mcp_server_url,
                allowed_tools=allowed,
            )
            return mcp

        except Exception as e:
            logger.exception("mcp_tool_creation_failed", error=str(e))
            return None


# ── Copilot MCP servers (5 servers for the lending flow) ────────

COPILOT_MCP_SERVERS = [
    {
        "label": "identity-kyc",
        "url_attr": "mcp_identity_url",
        "allowed_tools": ["verify_nafath", "verify_national_id", "get_customer_profile"],
    },
    {
        "label": "product-catalog",
        "url_attr": "mcp_product_url",
        "allowed_tools": ["list_loan_products", "get_product_details", "get_product_by_intent"],
    },
    {
        "label": "credit-eligibility",
        "url_attr": "mcp_credit_url",
        "allowed_tools": ["run_credit_check", "get_credit_score", "check_eligibility"],
    },
    {
        "label": "offers-pricing",
        "url_attr": "mcp_offers_url",
        "allowed_tools": [
            "generate_offer", "calculate_monthly_payment",
            "adjust_offer", "decline_offer",
        ],
    },
    {
        "label": "contract-disbursement",
        "url_attr": "mcp_contract_url",
        "allowed_tools": [
            "create_contract", "verify_otp",
            "disburse_funds", "get_contract_status",
        ],
    },
]


@lru_cache(maxsize=1)
def get_copilot_mcp_tools() -> tuple:
    """Create MCP tools for all 5 copilot servers.

    Returns a tuple (hashable for lru_cache) of McpTool instances.
    Only creates tools when ``MCP_COPILOT_ENABLED`` is True.
    """
    if not settings.mcp_copilot_enabled:
        logger.info("copilot_mcp_disabled")
        return ()

    tools = []
    for server in COPILOT_MCP_SERVERS:
        url = getattr(settings, server["url_attr"], "")
        if not url:
            logger.warning("copilot_mcp_skip", label=server["label"], reason="URL not set")
            continue

        try:
            mcp = create_mcp_tool(
                server_url=url,
                server_label=server["label"],
                allowed_tools=server["allowed_tools"],
                approval_mode="never",
            )
            tools.append(mcp)
            logger.info(
                "copilot_mcp_created",
                label=server["label"],
                url=url,
                tools=server["allowed_tools"],
            )
        except Exception as e:
            logger.exception("copilot_mcp_failed", label=server["label"], error=str(e))

    logger.info("copilot_mcp_tools_ready", count=len(tools))
    return tuple(tools)


def get_mcp_handler():
    """Create an ``McpRunHandler`` for all active MCP tools."""
    all_tools = []

    legacy = get_mcp_tool()
    if legacy is not None:
        all_tools.append(legacy)

    all_tools.extend(get_copilot_mcp_tools())

    if not all_tools:
        return None

    return McpRunHandler(mcp_tools=all_tools)
