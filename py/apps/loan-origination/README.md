# Loan Origination API

Mortgage loan origination assistant powered by Azure AI Foundry agents. Guides applicants through document upload, extraction, and pre-approval.

## Business Flow Context

This service implements the origination side of the LoanFlow AI vision:

- conversational intake
- document upload and quality checks
- document data extraction
- application summarization
- approval letter generation
- auditable action logging

It is designed to pair with a servicing experience for existing borrowers (portfolio Q&A, policy guidance, and eligibility exploration).

## Quick Start

```bash
cd py/apps/loan-origination
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Liveness probe |
| `POST` | `/api/v1/loan/stream` | SSE streaming chat |
| `POST` | `/api/v1/loan/upload` | Document upload |
| `GET` | `/api/v1/loan/{id}` | Application details |
| `GET` | `/api/v1/loan/{id}/audit` | Audit trail |
| `GET` | `/api/v1/loan/{id}/documents` | Document list |

## Environment Variables

See `core/config.py` for all settings. Key variables:

- `FOUNDRY_PROJECT_ENDPOINT` — Azure AI Foundry project endpoint
- `DOCUMENT_INTELLIGENCE_ENDPOINT` — Azure Document Intelligence endpoint
- `STORAGE_MODE` — `inmemory` (default) or `cosmos`

## Tests

```bash
uv run pytest -v
```
