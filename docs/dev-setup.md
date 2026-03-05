# Dev Setup — LoanFlow AI

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (Python package manager)
- Node 20+
- [`pnpm`](https://pnpm.io/) (Node package manager)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az`) — required for local Azure authentication

## Quick Start (all services)

Open **three terminals** and run the commands below in order.

### Terminal 1 — MCP Servers

```bash
cd py/mcp
pip install -r requirements.txt   # first time only
python run_all.py
```

This starts all 5 MCP mock servers:

| Server | Port | Endpoint |
|---|---|---|
| identity_kyc | 8010 | http://localhost:8010/mcp |
| product_catalog | 8011 | http://localhost:8011/mcp |
| credit_eligibility | 8012 | http://localhost:8012/mcp |
| offers_pricing | 8013 | http://localhost:8013/mcp |
| contract_disbursement | 8014 | http://localhost:8014/mcp |

> Press `Ctrl+C` to stop all servers.

### Terminal 2 — Backend

```bash
cd py/apps/loan-origination
uv sync                # install dependencies (first time / after changes)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

Backend runs on **http://localhost:8002**.

Key endpoints:
- Health check: `GET /healthz`
- API docs: `GET /docs`

### Terminal 3 — Frontend

**Option A — Loan UI (full app)**
```bash
cd ts/apps/loan-ui
pnpm install           # first time only
pnpm dev
```
Runs on **http://localhost:5174**.

**Option B — Agent UI (lightweight chat)**
```bash
cd ts/apps/uiAgent
pnpm install           # first time only
pnpm dev
```
Runs on **http://localhost:5176**.

Both frontends proxy `/api` requests to the backend on port 8002 automatically.

## Azure Authentication

The backend uses `DefaultAzureCredential`. For local development, authenticate via the Azure CLI:

```bash
az login
```

If `az` is not found, install it:
```bash
brew install azure-cli   # macOS
```

Verify your login:
```bash
az account show --query '{name:name, id:id}' -o table
```

## Environment Variables

Backend configuration is in `py/apps/loan-origination/core/config.py`. Key settings:

| Variable | Default | Description |
|---|---|---|
| `STORAGE_MODE` | `inmemory` | `inmemory` (local) or `cosmos` (Azure) |
| `OTEL_EXPORTER` | `console` | `console`, `aitoolkit`, or `azure` |
| `FOUNDRY_PROJECT_ENDPOINT` | — | Azure AI Foundry project endpoint |
| `MCP_COPILOT_ENABLED` | `true` | Enable the 5 MCP lending servers |
| `DOCUMENT_INTELLIGENCE_ENDPOINT` | — | Azure Document Intelligence URL |

Create a `.env` file in `py/apps/loan-origination/` to override any defaults.

## Docker Compose

Run everything in containers:
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
