# Dev Setup — LoanFlow AI

## Prerequisites

- Python 3.11+
- `uv`
- Node 20+
- `pnpm`

## Backend

```bash
cd py/apps/loan-origination
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

Backend runs on `http://localhost:8002`.

## Frontend

```bash
cd ts/apps/loan-ui
pnpm install
pnpm dev
```

Frontend runs on `http://localhost:5174`.

## Docker Compose

```bash
docker compose up --build
```

Services:
- Backend: `http://localhost:8002`
- Frontend: `http://localhost:5174`

## Validation Commands

```bash
# Backend
cd py/apps/loan-origination
uv run pytest tests -v

# Frontend
cd ts/apps/loan-ui
pnpm lint
pnpm type-check
```
