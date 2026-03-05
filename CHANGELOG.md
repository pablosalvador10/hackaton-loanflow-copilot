# Changelog

All notable changes to LoanFlow AI are documented in this file.

---

## [0.1.0] — 2026-03-05

### Loan Origination Migration + Full Docs Alignment

### Added

- New loan origination backend at `py/apps/loan-origination`
- New loan origination frontend at `ts/apps/loan-ui`
- Document workflow tools: quality validation, extraction, application assembly, approval letter generation, audit logging
- Loan streaming endpoint (`POST /api/v1/loan/stream`) and supporting upload/read/audit endpoints
- Loan-focused docs and instruction files

### Changed

- Root `README.md` migrated to LoanFlow AI business narrative (origination + servicing)
- `azure.yaml` switched primary services to loan backend/frontend
- `docker-compose.yml` switched primary local stack to loan backend/frontend
- `py/pyproject.toml` workspace metadata updated for loan scope
- All files under `docs/` migrated from VIN-centric language to loan-centric architecture and runbooks

### Removed

- VIN-specific project framing from primary docs paths
- Legacy VIN endpoint references from active runbooks

---

## [0.0.2] — 2026-03-04

### Streaming SSE + Tooling Foundation (Pre-migration)

- Introduced SSE chat streaming patterns and tool orchestration primitives used by current LoanFlow AI services.
- Introduced OpenTelemetry tracing and Cosmos-backed storage mode patterns.
- Introduced Terraform deployment modules (ACA, Cosmos, OpenAI, Foundry, Key Vault, observability).

---

## [0.0.1] — 2026-02-28

### Initial Prototype Foundation (Pre-migration)

- Monorepo scaffolding, FastAPI backend, React frontend, Foundry wrapper library, and local developer workflows.
