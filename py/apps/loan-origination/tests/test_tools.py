"""Unit tests for tool functions."""

from __future__ import annotations

import json

import pytest


class TestValidateDocument:
    """Tests for ``validate_document_quality``."""

    def test_stub_returns_passing_quality(self) -> None:
        """Without Document Intelligence configured, stub mode should return pass."""
        from tools.validate_document import validate_document_quality

        result = json.loads(
            validate_document_quality(
                document_id="doc-1",
                document_type="drivers_license",
                file_name="license.jpg",
                file_content_base64="fake_base64",
            )
        )

        assert result["quality_pass"] is True
        assert result["confidence_score"] >= 0.7
        assert result["document_id"] == "doc-1"


class TestExtractDocument:
    """Tests for ``extract_document_fields``."""

    def test_stub_extracts_drivers_license(self) -> None:
        """Stub mode should return mock extraction for drivers_license."""
        from tools.extract_document import extract_document_fields

        result = json.loads(
            extract_document_fields(
                document_id="doc-2",
                document_type="drivers_license",
                file_name="license.jpg",
                file_content_base64="fake_base64",
            )
        )

        assert result["document_id"] == "doc-2"
        assert "fields" in result
        assert "full_name" in result["fields"]

    def test_stub_extracts_w2(self) -> None:
        """Stub mode should return mock extraction for w2."""
        from tools.extract_document import extract_document_fields

        result = json.loads(
            extract_document_fields(
                document_id="doc-3",
                document_type="w2",
                file_name="w2.pdf",
                file_content_base64="fake_base64",
            )
        )

        assert result["document_id"] == "doc-3"
        assert "wages" in result["fields"] or "annual_income" in result["fields"]

    def test_stub_extracts_bank_statement(self) -> None:
        """Stub mode should return mock extraction for bank_statement."""
        from tools.extract_document import extract_document_fields

        result = json.loads(
            extract_document_fields(
                document_id="doc-4",
                document_type="bank_statement",
                file_name="statement.pdf",
                file_content_base64="fake_base64",
            )
        )

        assert result["document_id"] == "doc-4"
        assert "fields" in result


class TestAssembleApplication:
    """Tests for ``assemble_application``."""

    def test_assembles_basic_application(self) -> None:
        """Should compute DTI and return structured summary."""
        from tools.assemble_application import assemble_application

        result = json.loads(
            assemble_application(
                applicant_name="Jane Doe",
                applicant_annual_income=120000.0,
                applicant_monthly_debts=1500.0,
                applicant_total_assets=50000.0,
                property_address="123 Main St, Austin, TX 78701",
                purchase_price=400000.0,
                down_payment_percent=20.0,
                loan_term="30 years fixed",
            )
        )

        assert result["applicant"]["name"] == "Jane Doe"
        assert result["financing"]["purchase_price"] == 400000.0
        assert result["financing"]["mortgage_amount"] == 320000.0
        assert "dti_ratio" in result["financial_summary"]

    def test_assembles_with_co_applicant(self) -> None:
        """Should include co-applicant when provided."""
        from tools.assemble_application import assemble_application

        result = json.loads(
            assemble_application(
                applicant_name="Jane Doe",
                applicant_annual_income=120000.0,
                applicant_monthly_debts=1500.0,
                applicant_total_assets=50000.0,
                property_address="123 Main St",
                purchase_price=400000.0,
                down_payment_percent=20.0,
                loan_term="30 years fixed",
                co_applicant_name="John Doe",
                co_applicant_annual_income=80000.0,
            )
        )

        assert result["co_applicant"]["name"] == "John Doe"
        assert result["financial_summary"]["total_household_income"] == 200000.0


class TestGenerateLetter:
    """Tests for ``generate_approval_letter``."""

    def test_generates_letter_with_conditions(self) -> None:
        """Should return a markdown letter with conditions."""
        from tools.generate_letter import generate_approval_letter

        result = json.loads(
            generate_approval_letter(
                application_id="APP-001",
                applicant_name="Jane Doe",
                property_address="123 Main St, Austin, TX 78701",
                purchase_price=400000.0,
                mortgage_amount=320000.0,
                down_payment=80000.0,
                loan_term="30 years fixed",
                annual_income=120000.0,
                dti_ratio=28.5,
            )
        )

        assert "letter_content" in result
        assert "conditions" in result
        assert len(result["conditions"]) > 0
        assert "Jane Doe" in result["letter_content"]


class TestAuditLog:
    """Tests for ``log_audit_event``."""

    def test_logs_audit_event(self) -> None:
        """Should return confirmation with event_id and timestamp."""
        from tools.audit import log_audit_event

        result = json.loads(
            log_audit_event(
                application_id="APP-001",
                action_type="doc_uploaded",
                actor_type="applicant",
                details='{"document_type": "drivers_license"}',
            )
        )

        assert result["status"] == "recorded"
        assert result["application_id"] == "APP-001"
        assert "event_id" in result
        assert "timestamp" in result
