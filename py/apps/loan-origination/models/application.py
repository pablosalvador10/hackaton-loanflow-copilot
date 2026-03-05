"""Pydantic models for Loan Origination domain objects.

Five document types map to Cosmos DB containers:

- ``LoanApplication`` → ``applications``     (partitioned by ``/application_id``)
- ``DocumentRecord``  → ``documents``         (partitioned by ``/application_id``)
- ``Conversation``    → ``conversations``     (partitioned by ``/conversation_id``)
- ``AuditEvent``      → ``audit_events``      (partitioned by ``/application_id``)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


# ── Embedded models ──────────────────────────────────────────────


class ApplicantProfile(BaseModel):
    """Structured profile of a loan applicant (borrower or co-borrower).

    :param name: Full legal name.
    :param address: Mailing address.
    :param phone: Contact phone number.
    :param email: Contact email address.
    :param annual_income: Annual gross income in USD.
    :param employer: Current employer name.
    :param marital_status: Marital status.
    :param assets_total: Total verified assets in USD.
    :param liabilities_total: Total monthly liabilities in USD.
    """

    name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    annual_income: float = 0.0
    employer: str = ""
    marital_status: str = ""
    assets_total: float = 0.0
    liabilities_total: float = 0.0


# ── Top-level domain models ─────────────────────────────────────


class LoanApplication(BaseModel):
    """A mortgage loan application assembled from documents and user input.

    :param application_id: Unique identifier (partition key in Cosmos).
    :param applicant: Primary borrower profile.
    :param co_applicant: Co-borrower profile (optional).
    :param property_address: Address of the property being purchased.
    :param purchase_price: Total purchase price in USD.
    :param mortgage_amount: Requested loan amount in USD.
    :param down_payment: Down payment amount in USD.
    :param loan_term: Loan term description (e.g. ``"30 years fixed"``).
    :param dti_ratio: Debt-to-income ratio as a percentage.
    :param status: Application lifecycle status.
    :param created_at: ISO-8601 creation timestamp.
    :param updated_at: ISO-8601 last-update timestamp.
    """

    application_id: str = Field(default_factory=_new_id)
    applicant: ApplicantProfile = Field(default_factory=ApplicantProfile)
    co_applicant: ApplicantProfile | None = None
    property_address: str = ""
    purchase_price: float = 0.0
    mortgage_amount: float = 0.0
    down_payment: float = 0.0
    loan_term: str = "30 years fixed"
    dti_ratio: float = 0.0
    status: Literal[
        "draft", "submitted", "under_review", "approved", "rejected"
    ] = "draft"
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


class DocumentRecord(BaseModel):
    """Record of an uploaded document associated with a loan application.

    :param document_id: Unique identifier for the document.
    :param application_id: Parent application (partition key in Cosmos).
    :param document_type: Classification of the document.
    :param owner_role: Whether this belongs to the borrower or co-borrower.
    :param file_name: Original uploaded file name.
    :param upload_timestamp: ISO-8601 upload time.
    :param extraction_status: Current extraction pipeline status.
    :param verification_status: Whether the document has been verified.
    :param confidence_score: AI confidence score (0.0 – 1.0).
    :param quality_issues: List of quality problems found during validation.
    :param extracted_fields: Key-value pairs extracted from the document.
    :param blob_url: URL of the stored document (empty for in-memory dev).
    """

    document_id: str = Field(default_factory=_new_id)
    application_id: str = ""
    document_type: Literal[
        "drivers_license",
        "w2",
        "bank_statement",
        "pay_stub",
        "investment_statement",
        "other",
    ] = "other"
    owner_role: Literal["borrower", "co_borrower"] = "borrower"
    file_name: str = ""
    upload_timestamp: str = Field(default_factory=_utcnow)
    extraction_status: Literal[
        "pending", "processing", "completed", "failed"
    ] = "pending"
    verification_status: Literal[
        "unverified", "verified", "rejected"
    ] = "unverified"
    confidence_score: float = 0.0
    quality_issues: list[str] = Field(default_factory=list)
    extracted_fields: dict = Field(default_factory=dict)
    blob_url: str = ""


class Conversation(BaseModel):
    """A user conversation thread for loan origination.

    :param conversation_id: Stable thread ID (partition key in Cosmos).
    :param messages: Ordered list of ``{"role": ..., "content": ...}`` dicts.
    :param application_id: Associated application ID (if created).
    :param created_at: ISO-8601 creation timestamp.
    :param updated_at: ISO-8601 last-update timestamp.
    """

    conversation_id: str
    messages: list[dict] = Field(default_factory=list)
    application_id: str | None = None
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


class AuditEvent(BaseModel):
    """An auditable event in the loan origination workflow.

    :param event_id: Unique event identifier.
    :param application_id: Parent application (partition key in Cosmos).
    :param actor_type: Who triggered this event.
    :param action_type: What happened.
    :param details: Free-form detail payload.
    :param timestamp: ISO-8601 event timestamp.
    """

    event_id: str = Field(default_factory=_new_id)
    application_id: str = ""
    actor_type: Literal["system", "user", "reviewer"] = "system"
    action_type: Literal[
        "application_received",
        "doc_uploaded",
        "doc_validated",
        "doc_rejected",
        "extraction_complete",
        "application_assembled",
        "review_started",
        "approval_generated",
        "letter_sent",
    ] = "application_received"
    details: dict = Field(default_factory=dict)
    timestamp: str = Field(default_factory=_utcnow)
