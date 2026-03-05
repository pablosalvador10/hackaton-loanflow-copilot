"""Loan application assembly tool.

Takes extracted document fields and user-provided property / financing
details, computes DTI ratio, and builds a structured ``LoanApplication``.

This is a **synchronous** function (required by Foundry FunctionTool).
"""

from __future__ import annotations

import json

import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


def assemble_application(
    applicant_name: str,
    applicant_address: str,
    applicant_phone: str,
    applicant_email: str,
    applicant_annual_income: float,
    applicant_employer: str,
    applicant_marital_status: str,
    applicant_assets_total: float,
    applicant_liabilities_total: float,
    property_address: str,
    purchase_price: float,
    down_payment_percent: float,
    loan_term: str,
    co_applicant_name: str = "",
    co_applicant_annual_income: float = 0.0,
) -> str:
    """Assemble a structured loan application from extracted data.

    Combines applicant profile information (from document extraction)
    with user-provided property and financing details. Computes the
    mortgage amount, down payment, and debt-to-income ratio.

    :param applicant_name: Full legal name of the primary borrower.
    :param applicant_address: Mailing address of the primary borrower.
    :param applicant_phone: Contact phone number.
    :param applicant_email: Contact email address.
    :param applicant_annual_income: Annual gross income in USD.
    :param applicant_employer: Current employer name.
    :param applicant_marital_status: Marital status.
    :param applicant_assets_total: Total verified assets in USD.
    :param applicant_liabilities_total: Total monthly liabilities in USD.
    :param property_address: Address of the property being purchased.
    :param purchase_price: Total purchase price in USD.
    :param down_payment_percent: Down payment as a percentage of purchase price.
    :param loan_term: Loan term (e.g. ``"30 years fixed"``).
    :param co_applicant_name: Co-borrower name (optional).
    :param co_applicant_annual_income: Co-borrower annual income (optional).
    :return: JSON string with the assembled application summary.
    :raises RuntimeError: If computation or validation fails.
    """
    with tracer.start_as_current_span("tool.assemble_application") as span:
        span.set_attribute("tool.name", "assemble_application")
        span.set_attribute("tool.args.applicant_name", applicant_name)
        span.set_attribute("tool.args.property_address", property_address)
        span.set_attribute("tool.args.purchase_price", purchase_price)

        logger.info(
            "assemble_application_start",
            applicant_name=applicant_name,
            property_address=property_address,
            purchase_price=purchase_price,
        )

        try:
            # Compute derived fields
            down_payment = purchase_price * (down_payment_percent / 100.0)
            mortgage_amount = purchase_price - down_payment

            # DTI ratio: (monthly liabilities / monthly income) * 100
            total_annual_income = applicant_annual_income + co_applicant_annual_income
            monthly_income = total_annual_income / 12.0 if total_annual_income > 0 else 0.0
            dti_ratio = (
                (applicant_liabilities_total / monthly_income * 100.0)
                if monthly_income > 0
                else 0.0
            )

            from models.application import _new_id

            application_id = _new_id()

            application_summary = {
                "application_id": application_id,
                "status": "draft",
                "applicant": {
                    "name": applicant_name,
                    "address": applicant_address,
                    "phone": applicant_phone,
                    "email": applicant_email,
                    "annual_income": applicant_annual_income,
                    "employer": applicant_employer,
                    "marital_status": applicant_marital_status,
                    "assets_total": applicant_assets_total,
                    "liabilities_total": applicant_liabilities_total,
                },
                "co_applicant": {
                    "name": co_applicant_name,
                    "annual_income": co_applicant_annual_income,
                } if co_applicant_name else None,
                "property_address": property_address,
                "purchase_price": purchase_price,
                "mortgage_amount": round(mortgage_amount, 2),
                "down_payment": round(down_payment, 2),
                "down_payment_percent": down_payment_percent,
                "loan_term": loan_term,
                "dti_ratio": round(dti_ratio, 2),
                "total_household_income": total_annual_income,
                "total_assets": applicant_assets_total,
            }

            result_json = json.dumps(application_summary)

            span.set_attribute("tool.result.application_id", application_id)
            span.set_attribute("tool.result.mortgage_amount", mortgage_amount)
            span.set_attribute("tool.result.dti_ratio", dti_ratio)

            logger.info(
                "assemble_application_complete",
                application_id=application_id,
                mortgage_amount=mortgage_amount,
                dti_ratio=round(dti_ratio, 2),
            )

            return result_json

        except Exception as e:
            logger.exception(
                "assemble_application_error",
                applicant_name=applicant_name,
                error=str(e),
            )
            span.set_attribute("tool.error", str(e))
            raise RuntimeError(
                f"Application assembly failed: {e}"
            ) from e
