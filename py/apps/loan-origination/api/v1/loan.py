"""Loan Origination endpoints — conversational intake + document processing.

Provides endpoints:
- ``POST /api/v1/loan/stream``               — SSE streaming for the chat UI
- ``POST /api/v1/loan/upload``               — File upload for documents
- ``GET  /api/v1/loan/{application_id}``     — Get application details
- ``GET  /api/v1/loan/{application_id}/audit``   — Get audit trail
- ``GET  /api/v1/loan/{application_id}/documents`` — Get documents list

Uses a Foundry Prompt Agent with five FunctionTools:
1. ``validate_document_quality`` — checks document image quality
2. ``extract_document_fields``  — extracts structured data from documents
3. ``assemble_application``     — builds structured loan application
4. ``generate_approval_letter`` — creates pre-approval letter
5. ``log_audit_event``          — records audit trail events
"""

from __future__ import annotations

import asyncio
import base64
import json
import threading
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from foundrykit import AgentManager, AgentStreamEvent, ToolRegistry, get_foundry_client
from pydantic import BaseModel, Field

from models.application import AuditEvent, Conversation, DocumentRecord, LoanApplication
from services import mcp_functions as _mcp_fn_mod
from services.mcp_functions import register_mcp_functions
from services.mcp_setup import get_mcp_handler, get_mcp_tool
from services.storage import get_storage
from tools.assemble_application import assemble_application
from tools.audit import log_audit_event
from tools.extract_document import extract_document_fields
from tools.generate_letter import generate_approval_letter
from tools.validate_document import validate_document_quality

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["loan-origination"])

# ── Load system prompt ──────────────────────────────────────────
_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "loan_origination_system.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


# ── Request / Response models ───────────────────────────────────


class ChatMessage(BaseModel):
    """A single message in the conversation history.

    :param role: Either ``"user"`` or ``"assistant"``.
    :param content: The message text.
    """

    role: str
    content: str


class StreamRequest(BaseModel):
    """Request body for the SSE streaming endpoint (matches frontend contract).

    :param conversation_id: Stable ID for the conversation thread.
    :param message_id: Unique ID for this message turn.
    :param message: The user's latest message text.
    :param history: Previous messages in the conversation.
    :param application_id: Optional application ID for continued sessions.
    :param document_context: Optional base64-encoded document data injected by upload.
    """

    conversation_id: str
    message_id: str
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    application_id: str | None = None
    document_context: str | None = None


class UploadResponse(BaseModel):
    """Response from the document upload endpoint.

    :param document_id: Unique ID assigned to the uploaded document.
    :param file_name: Original file name.
    :param message: Instruction for the next step.
    """

    document_id: str
    file_name: str
    message: str


class ApplicationSummary(BaseModel):
    """Summarised loan application for GET responses."""

    application_id: str
    status: str
    applicant_name: str | None = None
    loan_amount: float | None = None
    created_at: str


# ── Tool registration ───────────────────────────────────────────

_registry = ToolRegistry()
_registry.register(validate_document_quality)
_registry.register(extract_document_fields)
_registry.register(assemble_application)
_registry.register(generate_approval_letter)
_registry.register(log_audit_event)

# Add MCP tool if configured (optional — enables remote tool servers)
# Note: only the legacy server (azure_specs) uses McpTool since it has a public URL.
# The 5 local copilot MCP servers are registered as Python FunctionTools below so
# the SDK calls them locally instead of routing through Foundry's cloud MCP connector.
_mcp = get_mcp_tool()
if _mcp is not None:
    _registry.add_mcp_tool(_mcp)
    logger.info("mcp_tool_registered", label=_mcp.server_label)

# Register all 16 local MCP tools as native function tools (local execution).
_mcp_fn_count = register_mcp_functions(_registry)
logger.info("mcp_functions_registered", count=_mcp_fn_count)

# Only pass the azure_specs McpTool object to run_agent_stream (for approval handling).
# Local MCP functions run automatically via the standard FunctionTool mechanism.
_all_mcp_tools = [_mcp] if _mcp is not None else []

_toolset = _registry.build_toolset()


# ── Card determination ──────────────────────────────────────────

# Tools in priority order — later tool in the list wins if multiple were called.
_CARD_PRIORITY: list[tuple[str, str]] = [
    ("verify_nafath",           "nafath-verify"),
    ("verify_national_id",      "identity-card"),
    ("get_customer_profile",    "identity-card"),
    ("list_loan_products",      "product-list"),
    ("get_product_by_intent",   "product-list"),
    ("run_credit_check",        "credit-check"),
    ("check_eligibility",       "credit-check"),
    ("get_credit_score",        "credit-score"),
    ("generate_offer",          "offer-card"),
    ("calculate_monthly_payment", "offer-card"),
    ("create_contract",         "contract-summary"),
]


def _determine_card(results: dict) -> dict | None:
    """Select the richest card to show based on which tools were called.

    Iterates priority list — the last matching entry wins so higher-value
    actions (offers, contracts) always take precedence.

    :param results: Dict of tool_name → parsed JSON result.
    :return: ``{type, data}`` dict ready for the ``card`` SSE event, or None.
    """
    chosen_type: str | None = None
    chosen_data: dict = {}

    for tool_name, card_type in _CARD_PRIORITY:
        if tool_name not in results:
            continue
        raw = results[tool_name]
        # product-list expects { products: [...] }
        if card_type == "product-list":
            data = {"products": raw} if isinstance(raw, list) else (raw if isinstance(raw, dict) else {})
        elif isinstance(raw, dict):
            data = raw
        else:
            data = {}
        chosen_type = card_type
        chosen_data = data

    if chosen_type is None:
        return None
    return {"type": chosen_type, "data": chosen_data}


# ── SSE helpers ─────────────────────────────────────────────────


def _sse_event(event: str, data: dict) -> str:
    """Format a single SSE event string.

    :param event: Event type name (``delta``, ``done``, ``error``).
    :param data: JSON-serialisable payload.
    :return: SSE-formatted string.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── SSE streaming endpoint ──────────────────────────────────────


@router.post(
    "/loan/stream",
    summary="Stream a loan origination conversation via SSE",
    description=(
        "Accepts a chat-style message with optional document context, "
        "and streams the agent's response as Server-Sent Events."
    ),
)
async def loan_stream(body: StreamRequest) -> StreamingResponse:
    """SSE endpoint for the loan origination chat UI.

    Runs the Foundry agent with full conversation history and streams
    text deltas as ``event: delta`` SSE events.

    :param body: Chat-style request with message, history and optional document context.
    :return: ``StreamingResponse`` with ``text/event-stream`` content type.
    """
    return StreamingResponse(
        _stream_loan_sse(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_loan_sse(body: StreamRequest) -> AsyncGenerator[str, None]:
    """Generate SSE events for a loan origination conversation turn.

    Flow:
    1. Build user message (may include document context from upload).
    2. Create a temporary Foundry agent with loan origination tools.
    3. Stream text deltas to the frontend.
    4. Persist the conversation turn.

    :param body: The stream request from the frontend.
    :return: Async generator of SSE-formatted strings.
    """
    logger.info(
        "loan_stream_request",
        conversation_id=body.conversation_id,
        application_id=body.application_id,
        has_document=body.document_context is not None,
    )

    try:
        client = get_foundry_client()
        manager = AgentManager(client)
        chunks: list[str] = []

        # Build user message — include conversation history and optional document context
        user_message = body.message
        if body.document_context:
            user_message = (
                f"{body.message}\n\n"
                f"[Document data attached — process this document]\n"
                f"Document context: {body.document_context}"
            )

        # Prepend conversation history so the agent has full context each turn.
        # The Azure Agents API only accepts user-role messages when adding to a
        # thread manually, so we inject the prior turns as a transcript prefix.
        if body.history:
            lines = ["[CONVERSATION HISTORY — do NOT repeat the welcome menu, continue naturally from where the conversation left off]"]
            for msg in body.history:
                label = "User" if msg.role == "user" else "Assistant"
                lines.append(f"{label}: {msg.content}")
            lines.append(f"[END OF HISTORY]\n\nUser: {user_message}")
            user_message = "\n".join(lines)

        # Run the synchronous Foundry SDK stream in a background thread so the
        # async event loop is never blocked.  Events are forwarded via a queue.
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[AgentStreamEvent | None] = asyncio.Queue()

        def _produce() -> None:
            """Run the agent stream in a worker thread, forwarding events to the queue."""
            _mcp_fn_mod.clear_tool_results()
            try:
                with manager.temporary_agent(
                    name="LoanOrigination",
                    instructions=_SYSTEM_PROMPT,
                    toolset=_toolset,
                ) as agent:
                    stream_kwargs: dict[str, Any] = {}
                    if _all_mcp_tools:
                        stream_kwargs["mcp_tools"] = _all_mcp_tools

                    for event in manager.run_agent_stream(
                        agent.id, user_message, **stream_kwargs
                    ):
                        loop.call_soon_threadsafe(queue.put_nowait, event)

                # After the agent finishes, capture tool results and forward
                tool_results = _mcp_fn_mod.get_tool_results()
                if tool_results:
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        AgentStreamEvent(
                            event_type="tool_results",
                            data="",
                            metadata={"results": tool_results},
                        ),
                    )
            except Exception as exc:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    AgentStreamEvent(event_type="error", data=str(exc)),
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        thread = threading.Thread(target=_produce, daemon=True)
        thread.start()

        while True:
            event = await queue.get()
            if event is None:
                break
            if event.event_type == "text_delta":
                chunks.append(event.data)
                yield _sse_event("delta", {"text": event.data})
            elif event.event_type == "tool_start":
                tool_names = (event.metadata or {}).get("tool_names", [])
                yield _sse_event("tool_start", {
                    "label": event.data,
                    "tool_names": tool_names,
                })
            elif event.event_type == "tool_complete":
                yield _sse_event("tool_done", {})
            elif event.event_type == "tool_results":
                card = _determine_card(event.metadata.get("results", {}))
                if card:
                    yield _sse_event("card", card)
            elif event.event_type == "error":
                yield _sse_event("error", {"message": event.data})

        thread.join(timeout=30)

        # Persist conversation
        full_response = "".join(chunks)
        storage = get_storage()

        conversation = Conversation(
            conversation_id=body.conversation_id,
            messages=[
                *[{"role": m.role, "content": m.content} for m in body.history],
                {"role": "user", "content": body.message},
                {"role": "assistant", "content": full_response},
            ],
            application_id=body.application_id,
        )
        await storage.upsert_conversation(conversation)

        yield _sse_event("done", {
            "application_id": body.application_id,
        })
        logger.info(
            "loan_stream_complete",
            conversation_id=body.conversation_id,
            application_id=body.application_id,
        )

    except Exception as e:
        logger.exception("loan_stream_error", error=str(e))
        yield _sse_event("error", {"message": f"Agent error: {e}"})
        yield _sse_event("done", {})


# ── Document upload endpoint ────────────────────────────────────


@router.post(
    "/loan/upload",
    response_model=UploadResponse,
    summary="Upload a document for the loan application",
    description=(
        "Accepts a document file (PDF, JPG, PNG) and returns a document_id. "
        "The document data is base64-encoded and can be passed to the "
        "streaming endpoint as document_context for processing."
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="The document file (PDF, JPG, PNG)"),
    document_type: str = Form(
        ...,
        description="Type of document: drivers_license, w2, bank_statement, pay_stub, investment_statement",
    ),
    application_id: str | None = Form(
        None,
        description="Optional application ID to associate the document with",
    ),
) -> UploadResponse:
    """Upload a document and receive a document_id + base64 payload.

    The frontend should then include the base64 data in the next
    streaming request as ``document_context`` so the agent can process it.

    :param file: Uploaded file.
    :param document_type: The category of the document.
    :param application_id: Optional link to an existing application.
    :return: Document ID and instructions.
    :raises HTTPException: On invalid file type or read error.
    """
    if file.content_type not in (
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Use PDF, JPG, or PNG.",
        )

    try:
        content = await file.read()
        b64_content = base64.b64encode(content).decode("utf-8")
        document_id = str(uuid.uuid4())

        logger.info(
            "document_uploaded",
            document_id=document_id,
            file_name=file.filename,
            document_type=document_type,
            size_bytes=len(content),
            application_id=application_id,
        )

        # Store minimal document record
        storage = get_storage()
        doc_record = DocumentRecord(
            document_id=document_id,
            application_id=application_id or "",
            document_type=document_type,
            file_name=file.filename or "unknown",
            status="uploaded",
        )
        await storage.create_document(doc_record)

        # Return the document_id and base64 for the frontend to attach to next message
        return UploadResponse(
            document_id=document_id,
            file_name=file.filename or "unknown",
            message=(
                f"Document '{file.filename}' uploaded successfully as {document_type}. "
                f"Send the document context in your next message to process it."
            ),
        )

    except Exception as e:
        logger.exception("document_upload_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process document upload.") from e


# ── Application detail endpoint ─────────────────────────────────


@router.get(
    "/loan/{application_id}",
    summary="Get loan application details",
    description="Retrieve the current state of a loan application.",
)
async def get_application(application_id: str) -> dict:
    """Retrieve a loan application by ID.

    :param application_id: The unique application identifier.
    :return: Application data or 404.
    :raises HTTPException: If application not found.
    """
    storage = get_storage()
    app = await storage.read_application(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app.model_dump()


# ── Audit trail endpoint ────────────────────────────────────────


@router.get(
    "/loan/{application_id}/audit",
    summary="Get audit trail for an application",
    description="Retrieve all audit events for a loan application.",
)
async def get_audit_trail(application_id: str) -> list[dict]:
    """Retrieve the audit trail for an application.

    :param application_id: The application to get events for.
    :return: List of audit events ordered by timestamp (desc).
    """
    storage = get_storage()
    events = await storage.list_audit_events(application_id)
    return [e.model_dump() for e in events]


# ── Documents list endpoint ─────────────────────────────────────


@router.get(
    "/loan/{application_id}/documents",
    summary="Get documents for an application",
    description="Retrieve all documents associated with a loan application.",
)
async def get_documents(application_id: str) -> list[dict]:
    """Retrieve all documents for an application.

    :param application_id: The application to get documents for.
    :return: List of document records.
    """
    storage = get_storage()
    docs = await storage.list_documents_by_application(application_id)
    return [d.model_dump() for d in docs]
