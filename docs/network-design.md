# Network Design — LoanFlow AI

This document reflects the **current** Terraform topology in `infra/main.tf`.

## Topology Summary

```
Internet
      ├─ HTTPS → frontend container app (port 80 container)
      └─ HTTPS → backend container app (port 8002 container)

Azure VNet (10.0.0.0/16)
      └─ snet-aca (10.0.0.0/23, delegated to Microsoft.App/environments)
                  └─ Container Apps Environment (VNet-injected)

Backend egress
      ├─ Cosmos DB endpoint (MI + RBAC)
      ├─ Azure AI Foundry endpoint (MI + RBAC)
      ├─ Azure Document Intelligence endpoint
      ├─ Key Vault endpoint (MI + RBAC)
      └─ Application Insights ingestion
```

## Key Network Decisions

- Frontend and backend are externally reachable via ACA ingress.
- ACA environment is VNet-injected into `snet-aca`.
- Backend target port is `8002`; frontend target port is `80`.
- Health probes are `/healthz` (backend) and `/` (frontend).

## Cosmos Connectivity (Current)

Current root Terraform sets:

- `module "cosmos"` with `enable_private_endpoint = false`

Implication:

- Cosmos currently uses endpoint access without a Private Endpoint in this stack.
- Data access still uses Managed Identity + Cosmos RBAC (no account keys in app code).

## Identity-Centric Access

The backend uses a user-assigned managed identity (`id-<env>-backend`) with role assignments to:

- Cosmos DB data access
- Azure OpenAI user role
- Key Vault secrets reader
- ACR pull

This keeps service-to-service auth out of source code and out of static secrets.

## DNS and TLS

- Public FQDNs are issued under `*.azurecontainerapps.io`.
- TLS is terminated at ACA ingress.
- Backend CORS origins are configured during provisioning (`infra/scripts/postprovision.sh`).

## Future Hardening Options

- Enable Cosmos Private Endpoint and private DNS zone wiring in the Terraform module.
- Add NSGs to control subnet-level ingress/egress.
- Introduce Azure Front Door/WAF for additional edge controls.
