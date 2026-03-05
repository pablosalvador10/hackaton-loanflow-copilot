"""Integration tests for the Loan Origination FastAPI endpoints.

These tests mock the Foundry agent layer entirely, exercising the FastAPI
routing, request validation, and error handling without requiring Azure
credentials.
"""

from __future__ import annotations

import base64
import io
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _build_client() -> TestClient:
    """Import the FastAPI ``app`` and wrap it in a ``TestClient``."""
    from main import app

    return TestClient(app)


@pytest.fixture()
def client():
    """Provide a ``TestClient`` for each test."""
    return _build_client()


# ── Health check ────────────────────────────────────────────────


class TestHealthz:
    """Tests for ``GET /healthz``."""

    def test_healthz_returns_ok(self, client) -> None:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ── Streaming endpoint ──────────────────────────────────────────


class TestLoanStreamEndpoint:
    """Tests for ``POST /api/v1/loan/stream``."""

    def test_stream_returns_sse_events(self, client) -> None:
        """A valid stream request should return SSE delta + done events."""
        mock_event = MagicMock()
        mock_event.event_type = "text_delta"
        mock_event.data = "Hello, welcome to your loan application!"

        mock_manager = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "agent-loan-1"

        @contextmanager
        def _temp_agent(**kwargs):
            yield mock_agent

        mock_manager.temporary_agent = _temp_agent
        mock_manager.run_agent_stream.return_value = [mock_event]

        with (
            patch("api.v1.loan.AgentManager", return_value=mock_manager),
            patch("api.v1.loan.get_foundry_client", return_value=MagicMock()),
        ):
            response = client.post(
                "/api/v1/loan/stream",
                json={
                    "conversation_id": "conv-1",
                    "message_id": "msg-1",
                    "message": "I want to start my loan application",
                },
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "event: delta" in body
        assert "Hello, welcome" in body
        assert "event: done" in body

    def test_stream_with_document_context(self, client) -> None:
        """A stream request with document context should include it in the agent call."""
        mock_event = MagicMock()
        mock_event.event_type = "text_delta"
        mock_event.data = "Processing your document..."

        mock_manager = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "agent-loan-2"

        @contextmanager
        def _temp_agent(**kwargs):
            yield mock_agent

        mock_manager.temporary_agent = _temp_agent
        mock_manager.run_agent_stream.return_value = [mock_event]

        with (
            patch("api.v1.loan.AgentManager", return_value=mock_manager),
            patch("api.v1.loan.get_foundry_client", return_value=MagicMock()),
        ):
            response = client.post(
                "/api/v1/loan/stream",
                json={
                    "conversation_id": "conv-2",
                    "message_id": "msg-2",
                    "message": "Here is my driver's license",
                    "document_context": "base64data_here",
                },
            )

        assert response.status_code == 200
        assert "Processing your document" in response.text

    def test_stream_validation_error_missing_fields(self, client) -> None:
        """A request missing required fields should return 422."""
        response = client.post("/api/v1/loan/stream", json={})
        assert response.status_code == 422


# ── Upload endpoint ─────────────────────────────────────────────


class TestUploadEndpoint:
    """Tests for ``POST /api/v1/loan/upload``."""

    def test_upload_pdf_returns_document_id(self, client) -> None:
        """Uploading a PDF should return a document_id."""
        pdf_content = b"%PDF-1.4 fake pdf content"
        response = client.post(
            "/api/v1/loan/upload",
            files={"file": ("test_doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"document_type": "w2"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "document_id" in body
        assert body["file_name"] == "test_doc.pdf"

    def test_upload_jpg_returns_document_id(self, client) -> None:
        """Uploading a JPG should return a document_id."""
        jpg_content = b"\xff\xd8\xff\xe0 fake jpg"
        response = client.post(
            "/api/v1/loan/upload",
            files={"file": ("license.jpg", io.BytesIO(jpg_content), "image/jpeg")},
            data={"document_type": "drivers_license"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "document_id" in body

    def test_upload_rejects_unsupported_type(self, client) -> None:
        """Uploading an unsupported file type should return 400."""
        response = client.post(
            "/api/v1/loan/upload",
            files={"file": ("doc.txt", io.BytesIO(b"text"), "text/plain")},
            data={"document_type": "w2"},
        )

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]


# ── Application detail endpoint ─────────────────────────────────


class TestApplicationEndpoint:
    """Tests for ``GET /api/v1/loan/{application_id}``."""

    def test_get_nonexistent_application_returns_404(self, client) -> None:
        """Requesting a missing application should return 404."""
        response = client.get("/api/v1/loan/nonexistent-id")
        assert response.status_code == 404

    def test_get_existing_application(self, client) -> None:
        """Requesting an existing application should return its data."""
        from models.application import LoanApplication
        from services.storage import get_storage

        storage = get_storage()

        import asyncio

        app = LoanApplication(status="intake")
        asyncio.get_event_loop().run_until_complete(storage.create_application(app))

        response = client.get(f"/api/v1/loan/{app.application_id}")
        assert response.status_code == 200
        assert response.json()["application_id"] == app.application_id


# ── Audit trail endpoint ────────────────────────────────────────


class TestAuditEndpoint:
    """Tests for ``GET /api/v1/loan/{application_id}/audit``."""

    def test_get_empty_audit_trail(self, client) -> None:
        """An application with no audit events should return an empty list."""
        response = client.get("/api/v1/loan/some-app-id/audit")
        assert response.status_code == 200
        assert response.json() == []


# ── Documents endpoint ──────────────────────────────────────────


class TestDocumentsEndpoint:
    """Tests for ``GET /api/v1/loan/{application_id}/documents``."""

    def test_get_empty_documents(self, client) -> None:
        """An application with no documents should return an empty list."""
        response = client.get("/api/v1/loan/some-app-id/documents")
        assert response.status_code == 200
        assert response.json() == []
