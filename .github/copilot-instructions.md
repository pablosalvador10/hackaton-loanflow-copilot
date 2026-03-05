# Copilot Instructions — RouteTech Sentinel (VIN Insight)

> Master context for AI coding agents in this repository.

## Project Overview

This repo hosts **VIN Insight**: a FastAPI backend + React/Vite frontend that decodes VINs through the NHTSA API and uses an Azure AI Foundry Prompt Agent to generate vehicle insight reports.

| Component | Path | Tech Stack |
|-----------|------|------------|
| Frontend | `/ts/apps/ui` | React + Vite, TypeScript, Tailwind, pnpm |
| Backend | `/py/apps/vin-insight` | Python 3.11+, FastAPI, uv, Ruff, pytest |
| Processor app | `/py/apps/processors` | Python worker entrypoint for async/background tasks |
| Shared Foundry SDK | `/py/libs/foundrykit` | Internal client/config wrappers for Foundry Agents |
| Infrastructure | `/infra` | Terraform + Azure Container Apps + azd |

## What Exists Today

- Primary API endpoint: `POST /api/v1/vin-insight`
- Streaming endpoint for chat UX: `POST /api/v1/vin-insight/stream` (SSE)
- Health endpoint: `GET /healthz`
- Backend storage modes: `inmemory` (local) and `cosmos` (Azure)
- Tool functions in backend: `decode_vin`, `validate_vin_response`, `create_claim`

## Repository Layout

```
/
├── .github/
│   ├── copilot-instructions.md
│   ├── coding-standards.md
│   └── instructions/
├── docs/
│   ├── dev-setup.md
│   ├── LOCAL-TESTING.md
│   ├── system-design.md
│   ├── security-design.md
│   ├── network-design.md
│   ├── processors-design.md
│   └── readme-instructions.md
├── py/
│   ├── pyproject.toml
│   ├── apps/
│   │   ├── vin-insight/
│   │   └── processors/
│   └── libs/
│       ├── foundrykit/
│       └── scripts/
├── ts/
│   └── apps/ui/
├── infra/
├── azure.yaml
└── docker-compose.yml
```

## Instruction Files

Path-specific instruction files are in `.github/instructions/`:

- `frontend.instructions.md` (applies to `ts/apps/ui/**`)
- `backend.instructions.md` (applies to `py/apps/vin-insight/**`)
- `typescript.instructions.md` (`**/*.ts`, `**/*.tsx`, `**/*.js`, `**/*.jsx`)
- `python.instructions.md` (`**/*.py`)
- `infrastructure.instructions.md` (Terraform/Docker/deployment files)
- `tracing.instructions.md` (OpenTelemetry guidance)

## Key Conventions

### Backend

- Use `uv` commands from `py/apps/vin-insight/pyproject.toml`
- Keep API contracts in Pydantic models
- Use `structlog` (never `print()`)
- Keep tool spans instrumented with OpenTelemetry
- Respect storage abstraction in `services/storage.py`

### Frontend

- Use React + Vite SPA patterns (no Next.js assumptions)
- Keep TypeScript strict; avoid `any`
- Keep UI logic in `src/components`, `src/hooks`, `src/lib`

### Infra

- Terraform under `infra/` is source of truth
- `azure.yaml` maps `backend` and `frontend` services for azd
- Container Apps use backend port `8001` and frontend port `80`

## Runtime Settings (Important)

Backend config is defined in `py/apps/vin-insight/core/config.py`.

- `STORAGE_MODE`: `inmemory` or `cosmos`
- `OTEL_EXPORTER`: `console`, `aitoolkit`, or `azure`
- `FOUNDRY_CREDENTIAL_MODE`: `dev` or `managed_identity`
- `FOUNDRY_PROJECT_ENDPOINT`: Foundry project endpoint

## Local Commands

Backend (`py/apps/vin-insight`):

```bash
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8001
uv run pytest -v
uv run ruff check .
```

Frontend (`ts/apps/ui`):

```bash
pnpm install
pnpm dev
pnpm lint
pnpm type-check
```

## Do / Don’t

Do:

- Follow existing file/module patterns
- Keep changes scoped to the task
- Update docs when behavior or structure changes

Don’t:

- Reintroduce old `apirouter`/Contoso assumptions
- Commit secrets or real `.env` files
- Add custom UI primitives where existing patterns already work

## Documentation Pointers

- Setup: `docs/dev-setup.md`
- Testing: `docs/LOCAL-TESTING.md`
- Architecture: `docs/system-design.md`
- Security: `docs/security-design.md`
- Network: `docs/network-design.md`
- Processor notes: `docs/processors-design.md`
