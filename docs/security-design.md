# Security Design — LoanFlow AI

This document describes the **current** security baseline for LoanFlow AI.

## Security Pillars in This Repo

1. Managed identities for service-to-service Azure access.
2. RBAC roles scoped per resource (Cosmos/OpenAI/KeyVault/ACR).
3. Environment-driven runtime modes for local-vs-cloud behavior.
4. Structured logging + OpenTelemetry for traceability.

## Current Controls

### Identity and secrets

- Backend container app uses a user-assigned managed identity.
- Terraform wires RBAC grants for Azure dependencies.
- Application code does not rely on Cosmos keys in normal Azure deployment mode.

### Data and storage

- Storage abstraction supports `inmemory` and `cosmos` via `STORAGE_MODE`.
- Cosmos containers are provisioned for loan workflow entities such as `applications`, `documents`, `conversations`, and `audit_events`.
- Current root Terraform sets Cosmos private endpoint to disabled (`enable_private_endpoint = false`), so hardening here is a known follow-up option.

### Observability and auditability

- Backend uses `structlog` for structured logs.
- OpenTelemetry exports are selectable (`console`, `aitoolkit`, `azure`).
- Tool and storage operations are instrumented for trace correlation.

## Threats Addressed

- Secret leakage from source code or static config.
- Untracked failures in external dependencies.
- Data integrity gaps from ad-hoc storage writes.

## Remaining Hardening Opportunities

- Enable Cosmos private endpoint + private DNS integration.
- Add explicit auth layer for frontend/backend ingress if required by environment policy.
- Add tighter network controls (NSGs, edge WAF) in infra.

## Local Development Safety Model

- Default local mode uses `STORAGE_MODE=inmemory` and local tracing exporters.
- This keeps local onboarding simple while avoiding production credentials in day-to-day development.
