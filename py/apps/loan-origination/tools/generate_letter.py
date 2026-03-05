"""Approval letter generation tool.

Generates a formal pre-approval letter based on a completed loan
application. The letter includes editable fields, conditions, and
a professional format suitable for sending to the applicant.

This is a **synchronous** function (required by Foundry FunctionTool).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


def generate_approval_letter(
    application_id: str,
    applicant_name: str,
    applicant_address: str,
    property_address: str,
    purchase_price: float,
    mortgage_amount: float,
    down_payment: float,
    loan_term: str,
    dti_ratio: float,
    co_applicant_name: str = "",
    total_household_income: float = 0.0,
    total_assets: float = 0.0,
) -> str:
    """Generate a formal loan pre-approval letter.

    Creates a professional approval letter with all required details,
    conditions to be met, and standard disclaimers. The letter is
    returned as Markdown for rendering and editing.

    :param application_id: The loan application ID.
    :param applicant_name: Full name of the primary borrower.
    :param applicant_address: Mailing address of the primary borrower.
    :param property_address: Address of the property being purchased.
    :param purchase_price: Total purchase price in USD.
    :param mortgage_amount: Approved loan amount in USD.
    :param down_payment: Down payment amount in USD.
    :param loan_term: Loan term description.
    :param dti_ratio: Debt-to-income ratio as a percentage.
    :param co_applicant_name: Co-borrower name (optional).
    :param total_household_income: Combined annual household income.
    :param total_assets: Total verified assets.
    :return: JSON string with the generated letter content and metadata.
    :raises RuntimeError: If letter generation fails.
    """
    with tracer.start_as_current_span("tool.generate_approval_letter") as span:
        span.set_attribute("tool.name", "generate_approval_letter")
        span.set_attribute("tool.args.application_id", application_id)
        span.set_attribute("tool.args.applicant_name", applicant_name)

        logger.info(
            "generate_approval_letter_start",
            application_id=application_id,
            applicant_name=applicant_name,
        )

        try:
            today = datetime.now(UTC).strftime("%B %d, %Y")

            borrower_line = applicant_name
            if co_applicant_name:
                borrower_line += f" and {co_applicant_name}"

            letter_content = f"""# Loan Pre-Approval Letter

**Date:** {today}

**To:**
{applicant_name}
{applicant_address}

---

**RE: Pre-Approval for Mortgage Financing**
**Application ID:** {application_id}

---

Dear {applicant_name},

We are pleased to inform you that your application for mortgage financing has been **pre-approved** based on our review of your submitted documentation and financial information.

## Loan Details

| Detail | Value |
|--------|-------|
| **Borrower(s)** | {borrower_line} |
| **Property Address** | {property_address} |
| **Purchase Price** | ${purchase_price:,.2f} |
| **Loan Amount** | ${mortgage_amount:,.2f} |
| **Down Payment** | ${down_payment:,.2f} |
| **Loan Term** | {loan_term} |
| **Debt-to-Income Ratio** | {dti_ratio:.1f}% |

## Financial Summary

- **Total Household Income:** ${total_household_income:,.2f}
- **Total Verified Assets:** ${total_assets:,.2f}

## Conditions for Final Approval

This pre-approval is subject to the following conditions being met:

1. **Satisfactory Purchase Agreement** — A fully executed purchase agreement for the subject property must be provided.
2. **Property Appraisal** — The property must appraise at or above the purchase price of ${purchase_price:,.2f}.
3. **Clear Title** — A title search must confirm marketable title to the property with no outstanding liens or encumbrances.
4. **Property Insurance** — Proof of adequate homeowner's insurance coverage must be obtained.
5. **Employment Verification** — Current employment and income must be verified prior to closing.
6. **No Material Changes** — There must be no material adverse changes to your financial situation, credit profile, or employment status prior to closing.

## Important Disclaimers

- This letter constitutes a **pre-approval** and is not a binding commitment to lend.
- Final approval is contingent upon satisfactory completion of all conditions listed above.
- This pre-approval is valid for **90 days** from the date of this letter.
- Interest rates are subject to market conditions at the time of rate lock.
- All information provided in your application is subject to verification.

---

We look forward to assisting you through the financing process. Please do not hesitate to contact us if you have any questions.

Sincerely,

**AcmeCorp Lending**
Mortgage Operations Team
"""

            conditions = [
                "Satisfactory purchase agreement for the subject property",
                f"Property appraisal at or above ${purchase_price:,.2f}",
                "Clear and marketable title to the property",
                "Proof of adequate homeowner's insurance",
                "Current employment and income verification",
                "No material adverse changes to financial situation",
            ]

            result = {
                "application_id": application_id,
                "letter_content": letter_content,
                "generated_at": today,
                "conditions": conditions,
                "valid_for_days": 90,
                "applicant_name": applicant_name,
                "property_address": property_address,
                "mortgage_amount": mortgage_amount,
            }

            result_json = json.dumps(result)
            span.set_attribute("tool.result.letter_length", len(letter_content))

            logger.info(
                "generate_approval_letter_complete",
                application_id=application_id,
                letter_length=len(letter_content),
            )

            return result_json

        except Exception as e:
            logger.exception(
                "generate_approval_letter_error",
                application_id=application_id,
                error=str(e),
            )
            span.set_attribute("tool.error", str(e))
            raise RuntimeError(
                f"Approval letter generation failed: {e}"
            ) from e
