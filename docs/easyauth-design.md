# EasyAuth Notes — LoanFlow AI

This document records the current authentication posture for LoanFlow AI and how EasyAuth would fit if enabled later.

## Current State

- The current Terraform in `infra/main.tf` does **not** configure Container Apps EasyAuth.
- Frontend and backend Container Apps are internet-exposed through ACA ingress.
- Backend protection today is application-level behavior and deployment configuration; there is no EasyAuth policy in this repo.

## Why This File Exists

This repository inherited documentation from a previous project that had an EasyAuth automation flow. That flow is not present in LoanFlow AI today, so this file is intentionally a scoped reference, not an active runbook.

## If You Want EasyAuth in LoanFlow AI

Recommended high-level approach:

1. Create an Entra app registration for frontend gatekeeping.
2. Configure ACA auth (`authConfigs/current`) for the `ca-frontend-*` app.
3. Choose sign-in audience (`AzureADMyOrg` vs multi-tenant) based on tenant policy.
4. Validate frontend still reaches backend for API calls after auth redirect.

## Design Considerations

- EasyAuth protects access to the frontend URL and static assets.
- It is complementary to API authentication and authorization.
- If added, prefer automation under `infra/scripts/` and keep behavior idempotent.

## Validation Checklist (Future)

- `curl -I https://<frontend-fqdn>` returns auth challenge/redirect when unauthenticated.
- Authenticated users can load the SPA and call `/api/v1/loan/stream` and related loan APIs.
- CORS and redirect URIs are explicitly configured for each environment.

## Out of Scope

- No `enable-easyauth.sh` script exists in this repo today.
- No EasyAuth Terraform module is defined today.
