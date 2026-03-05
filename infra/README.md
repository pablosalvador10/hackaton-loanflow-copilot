# Infrastructure — LoanFlow AI

Terraform-managed Azure infrastructure provisioned via [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/).

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Resource Group: rg-{env}                                            │
│                                                                      │
│  ┌─── VNet (10.0.0.0/16) ───────────────────────────────────────┐    │
│  │                                                               │    │
│  │  snet-aca (10.0.0.0/23)                                      │    │
│  │  ┌──────────────────────┐                                     │    │
│  │  │ Container Apps Env   │                                     │    │
│  │  │  ├ ca-backend (8002) │                                     │    │
│  │  │  └ ca-frontend (80)  │                                     │    │
│  │  └──────────────────────┘                                     │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────┐ ┌───────────┐       │
│  │ ACR         │ │ Log Analytics│ │ App Ins.  │ │ Key Vault │       │
│  └─────────────┘ └──────────────┘ └───────────┘ └───────────┘       │
│                                                                      │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐      │
│  │ Cosmos DB (NoSQL)        │  │ Azure OpenAI (3 models)     │      │
│  │  └ loan-origination      │  │  ├ gpt-4-1-nano             │      │
│  │    ├ applications        │  │  ├ gpt-4-1-mini             │      │
│  │    ├ documents           │  │  └ gpt-4-1 (full)           │      │
│  │    ├ conversations       │  └──────────────────────────────┘      │
│  │    └ audit_events        │                                       │
│  └──────────────────────────┘                                        │
│                                                                      │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐      │
│  │ User-Assigned MI         │  │ AI Foundry (AI Services)    │      │
│  │  → ACR Pull              │  │  └ Prompt Agent hosting     │      │
│  │  → Cosmos RBAC           │  └──────────────────────────────┘      │
│  │  → OpenAI User           │                                        │
│  │  → Key Vault Reader      │                                        │
│  └──────────────────────────┘                                        │
└──────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Terraform >= 1.5](https://developer.hashicorp.com/terraform/install)

### Deploy with azd

```bash
# Login to Azure
azd auth login

# Initialize environment (first time only)
azd init

# Provision + build + deploy (all in one)
azd up
```

Or step-by-step:

```bash
azd provision      # Terraform infra + postprovision hook
azd deploy         # Build containers + push to ACA
```

After provisioning, `.env.azure` files are generated automatically:
- `py/apps/loan-origination/.env.azure` — Foundry, Cosmos, OpenTelemetry config
- `ts/apps/loan-ui/.env.azure` — backend URL for the frontend

### Provision manually (Terraform only)

```bash
cd infra
terraform init
terraform plan -var-file=main.tfvars.json
terraform apply -var-file=main.tfvars.json

# Then generate .env files
cd ..
python py/libs/scripts/write_env_from_tf.py
```

## Structure

```
infra/
├── main.tf                           # Root: all module calls, networking, identity, role assignments
├── provider.tf                       # Terraform + provider version pins (azurerm ~> 4.0, azuread ~> 3.0)
├── backend.tf                        # Remote state backend (commented template)
├── variables.tf                      # All input variables with validations
├── outputs.tf                        # azd-consumed outputs (AZURE_*, SERVICE_*)
├── provider.conf.json                # azd provider config
├── main.tfvars.json                  # azd variable mapping (${AZURE_ENV_NAME}, etc.)
├── README.md                         # This file
├── scripts/
│   └── postprovision.sh              # Post-provision: wires CORS, generates .env.azure files
└── modules/
    ├── log-analytics/main.tf         # Log Analytics workspace
    ├── application-insights/main.tf  # Application Insights (workspace-based)
    ├── container-registry/main.tf    # ACR + AcrPull role assignments
    ├── container-apps-environment/   # CAE (VNet-injected)
    │   └── main.tf
    ├── container-app/main.tf         # Generic container app (secrets, probes, env vars)
    ├── key-vault/main.tf             # Key Vault (RBAC-based, no access policies)
    ├── cosmos-db/main.tf             # Cosmos DB NoSQL + RBAC
    ├── openai/main.tf                # Azure OpenAI + multi-model deployments + RBAC
    └── ai-foundry/main.tf            # Azure AI Services (hub + project) + model deployments
```

## Modules

Each module follows the **single-file pattern** (variables + resources + outputs in one `main.tf`) for simplicity.

| Module | Purpose | Key Features |
|--------|---------|-------------|
| `log-analytics` | Centralized log collection | PerGB2018 SKU, configurable retention |
| `application-insights` | APM + OpenTelemetry export | Workspace-based, connection string output |
| `container-registry` | Docker image storage | AcrPull role assignments for managed identities |
| `container-apps-environment` | ACA hosting environment | VNet-injected via infrastructure subnet |
| `container-app` | Generic container app | Secrets, health probes, lifecycle ignore on image+env |
| `key-vault` | Secrets management | RBAC-based (no access policies), Secrets Officer + User roles |
| `cosmos-db` | Document database | Dynamic containers (applications, documents, conversations, audit_events), custom SQL RBAC role |
| `openai` | LLM model hosting | Multi-model deployments via `for_each`, Cognitive Services OpenAI User RBAC |
| `ai-foundry` | AI Services hub | `azurerm_ai_services` + project + backing storage, model deployments for Agents API |

## Feature Flags

| Variable | Default | Effect when `false` |
|----------|---------|-------------------|
| `enable_cosmos_db` | `true` | Skip Cosmos DB (backend uses `STORAGE_MODE=inmemory`) |
| `enable_openai` | `true` | Skip Azure OpenAI model deployments |
| `enable_ai_foundry` | `true` | Skip AI Foundry (AI Services hub + project + storage) |
| `enable_key_vault` | `true` | Skip Key Vault provisioning |

## OpenAI Models

Three model deployments are provisioned by default:

| Deployment Name | Model | Use Case |
|----------------|-------|----------|
| `gpt-4-1-nano` | gpt-4.1-nano | Fast, low-cost operations |
| `gpt-4-1-mini` | gpt-4.1-mini | Balanced — summaries, validation |
| `gpt-4-1` | gpt-4.1 | Full capability — loan assistant synthesis and reasoning |

Configure via the `openai_models` variable in `variables.tf`.

## Security

- **No secrets in state**: Cosmos uses Managed Identity RBAC (no keys). App Insights connection string passed as container secret.
- **VNet isolation**: ACA runs inside the VNet within a dedicated subnet.
- **RBAC everywhere**: Key Vault uses `enable_rbac_authorization`, Cosmos uses custom SQL role, OpenAI uses Cognitive Services User role.
- **Least privilege**: Backend MI gets only the roles it needs (AcrPull, Cosmos ReadWrite, OpenAI User, KV Secrets User).

## Outputs

All outputs use the `AZURE_*` or `SERVICE_*` prefix convention consumed by azd:

| Output | Description |
|--------|-------------|
| `AZURE_RESOURCE_GROUP_NAME` | Resource group name |
| `AZURE_CONTAINER_REGISTRY_LOGIN_SERVER` | ACR login server |
| `SERVICE_BACKEND_URI` | Backend container app HTTPS URL |
| `SERVICE_FRONTEND_URI` | Frontend container app HTTPS URL |
| `AZURE_COSMOS_ENDPOINT` | Cosmos DB endpoint |
| `AZURE_COSMOS_DATABASE_NAME` | Cosmos DB database name |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_AI_FOUNDRY_PROJECT_ENDPOINT` | AI Foundry project endpoint |
| `AZURE_APPINSIGHTS_CONNECTION_STRING` | Application Insights connection string |
| `AZURE_KEY_VAULT_URI` | Key Vault URI |
| `AZURE_OPENAI_DEPLOYMENT_NANO` | Nano model deployment name |
| `AZURE_OPENAI_DEPLOYMENT_MINI` | Mini model deployment name |
| `AZURE_OPENAI_DEPLOYMENT_FULL` | Full model deployment name |
| `AZURE_AI_SERVICES_ENDPOINT` | AI Foundry services endpoint |
| `AZURE_APPINSIGHTS_CONNECTION_STRING` | App Insights connection string (sensitive) |
| `AZURE_MANAGED_IDENTITY_CLIENT_ID` | Backend MI client ID |
| `CONTOSO_TENANT_ID` | Entra ID tenant |
| `CONTOSO_API_CLIENT_ID` | API app registration client ID |
| `CONTOSO_WEB_CLIENT_ID` | SPA app registration client ID |
| `CONTOSO_API_SCOPE` | Full scope URI (`api://{client_id}/access_as_user`) |
| `CONTOSO_API_AUDIENCE` | API audience (`api://{client_id}`) |
| `SB_NAMESPACE` | Service Bus namespace FQDN |
| `PROCESSOR_JOB` | Container Apps Job name for handoff processor |
