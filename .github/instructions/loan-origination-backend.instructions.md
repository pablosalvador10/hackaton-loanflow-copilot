---
applyTo: "py/apps/loan-origination/**"
---

# Loan Origination Backend Instructions

## Overview

The **Loan Origination** backend is a FastAPI application that orchestrates mortgage
loan applications via an Azure AI Foundry prompt agent tailored for financial
document processing and loan decisioning.

## Tech Stack

- **Python 3.11+** with `uv` for dependency management
- **FastAPI** for HTTP/SSE endpoints
- **Azure AI Foundry Agent SDK** via the shared `foundrykit` library
- **Azure Document Intelligence** for document extraction
- **structlog** for structured logging
- **OpenTelemetry** for distributed tracing

## Key Paths

| Path | Purpose |
|------|---------|
| `main.py` | FastAPI app entry point (port 8002) |
| `api/v1/loan.py` | Router — stream, upload, application, audit, docs |
| `core/config.py` | `LoanOriginationSettings` (Pydantic Settings) |
| `models/application.py` | Domain models: Application, Document, Audit |
| `services/storage.py` | Storage protocol + InMemory + Cosmos |
| `tools/` | Tool functions: validate, extract, assemble, letter, audit |
| `prompts/` | System prompt for the Foundry agent |

## Running Locally

```bash
cd py/apps/loan-origination
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

## Running Tests

```bash
cd py/apps/loan-origination
uv run pytest -v
uv run ruff check .
```

## Tool Functions

All tools are **synchronous** and return `str` (JSON). This is required by
the Foundry `FunctionTool` spec.

1. `validate_document_quality` — Uses Document Intelligence `prebuilt-read` to check quality
2. `extract_document_fields` — Maps document type → pre-built model for extraction
3. `assemble_application` — Computes DTI ratio and builds the application summary
4. `generate_approval_letter` — Produces a Markdown pre-approval letter
5. `log_audit_event` — Appends an event to the audit trail

### Stub Mode

When `DOCUMENT_INTELLIGENCE_ENDPOINT` is not configured, tools 1–2 return
realistic mock data. This enables local development without Azure resources.

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `FOUNDRY_PROJECT_ENDPOINT` | — | Required for agent calls |
| `FOUNDRY_CREDENTIAL_MODE` | `dev` | `dev` or `managed_identity` |
| `STORAGE_MODE` | `inmemory` | `inmemory` or `cosmos` |
| `DOCUMENT_INTELLIGENCE_ENDPOINT` | — | Optional; enables real doc processing |
| `DOCUMENT_INTELLIGENCE_KEY` | — | Optional; if using key-based auth |
| `MCP_SERVER_URL` | — | Optional; enables remote MCP tool server |
| `MCP_SERVER_LABEL` | `lending-mcp` | Label for the MCP server |
| `MCP_API_KEY` | — | Optional; auth header for MCP server |
| `MCP_ALLOWED_TOOLS` | — | Comma-separated whitelist of MCP tool names |
| `MCP_APPROVAL_MODE` | `never` | `never` (auto-approve) or `always` |
| `API_PORT` | `8002` | |
| `CORS_ORIGINS` | `http://localhost:5174` | |

## Conventions

- Use `structlog` — never `print()`
- Keep tool functions in `tools/` with one function per file
- Keep API contracts in Pydantic models
- Instrument tool spans with OpenTelemetry
- Respect the storage abstraction in `services/storage.py`
