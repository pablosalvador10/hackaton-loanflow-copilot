"""Loan Origination — FastAPI application entry point.

Wires up:
- Structured logging (``structlog``)
- OpenTelemetry tracing (console / AI Toolkit / Azure Monitor)
- CORS middleware
- v1 API routes (loan origination)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.loan import router as loan_router
from core.config import settings
from core.logging import configure_logging
from core.telemetry import configure_tracing, instrument_fastapi

# ── Tracing and logging configured at module level ───────────────
configure_logging(settings.log_level)
configure_tracing(settings.otel_exporter)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan (no-op; logging + tracing configured at module level)."""
    yield


app = FastAPI(
    title="Loan Origination API",
    version="0.1.0",
    description=(
        "Mortgage loan origination assistant powered by Azure AI Foundry agents. "
        "Guides applicants through document upload, extraction, and pre-approval."
    ),
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# ── Instrument FastAPI immediately after creation ────────────────
instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Public endpoints ─────────────────────────────────────────────


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness / readiness probe (unauthenticated)."""
    return {"status": "ok"}


# ── v1 API router ────────────────────────────────────────────────

app.include_router(loan_router)
