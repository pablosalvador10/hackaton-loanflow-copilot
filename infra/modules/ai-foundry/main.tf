# ═══════════════════════════════════════════════════════════════════
#  AI Foundry Module — Account + Project (New Foundry Model)
# ═══════════════════════════════════════════════════════════════════
#
#  Uses the NEW Foundry architecture (not the legacy Hub-based model):
#    - Azure AI Services account (CognitiveServices/accounts kind=AIServices
#      with allowProjectManagement=true)
#    - AI Foundry Project (CognitiveServices/accounts/projects) — child of account
#    - Model deployments on the AI Services account
#    - RBAC assignments for the backend managed identity
#
#  This is REQUIRED for the Agents API (azure-ai-projects SDK v2.x).
#  The legacy azurerm_ai_foundry / azurerm_ai_foundry_project resources create
#  Hub-based projects (MachineLearningServices/workspaces) which are NOT
#  compatible with the current Agents API or SDK.
#
#  Why azapi_resource?
#    - azurerm_ai_services does not expose "allowProjectManagement"
#    - azurerm has no resource for CognitiveServices/accounts/projects
#    - The official Microsoft foundry-samples Terraform templates use azapi
#
#  Reference:
#    - https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure
#    - https://learn.microsoft.com/en-us/azure/foundry/agents/environment-setup
#    - https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/use-your-own-resources
# ═══════════════════════════════════════════════════════════════════

terraform {
  required_providers {
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.5"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# ── Variables ───────────────────────────────────────────────────

variable "name" {
  description = "Base name for the AI Foundry resources"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "resource_group_id" {
  description = "Resource group ID (used for azapi parent_id)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "application_insights_id" {
  description = "Application Insights resource ID (kept for interface compat; future connection support)"
  type        = string
  default     = ""
}

variable "key_vault_id" {
  description = "Key Vault resource ID (kept for interface compat; future connection support)"
  type        = string
  default     = ""
}

variable "openai_resource_id" {
  description = "Azure OpenAI resource ID (unused — models deploy directly on AI Services account)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

variable "backend_identity_principal_id" {
  description = "Principal ID of the backend managed identity for RBAC"
  type        = string
  default     = ""
}

variable "model_deployments" {
  description = "Model deployments to create on the AI Foundry account"
  type = list(object({
    name          = string
    model_name    = string
    model_version = string
    sku_name      = optional(string, "GlobalStandard")
    sku_capacity  = optional(number, 150)
  }))
  default = []
}

variable "public_network_access" {
  description = "Whether public network access is enabled. Possible values: Enabled, Disabled."
  type        = string
  default     = "Enabled"
}

# ── AI Foundry Account ─────────────────────────────────────────
#
# CognitiveServices/accounts with kind=AIServices and allowProjectManagement=true.
# This is the "new Foundry" resource — NOT the legacy Hub.
#
# The critical property is `allowProjectManagement = true` which enables this
# account to host Foundry projects (child resources). Without it, the Agents
# API returns "project does not exist" (404).

resource "azapi_resource" "ai_foundry_account" {
  type                      = "Microsoft.CognitiveServices/accounts@2025-04-01-preview"
  name                      = "ais-${var.name}"
  parent_id                 = var.resource_group_id
  location                  = var.location
  schema_validation_enabled = false

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }
    properties = {
      # ═══════════════════════════════════════════════════════════
      #  allowProjectManagement = true
      #  THIS IS THE CRITICAL PROPERTY that makes the Agents API work.
      #  Without it, the account is just a regular CognitiveServices
      #  account and cannot host Foundry projects.
      # ═══════════════════════════════════════════════════════════
      allowProjectManagement = true

      # Custom subdomain is required for the .services.ai.azure.com endpoint
      customSubDomainName = "ais-${var.name}"

      # Network access
      publicNetworkAccess = var.public_network_access
      networkAcls = {
        defaultAction = "Allow"
      }

      # Keep local auth enabled for now (can be disabled later)
      disableLocalAuth = false
    }
  }

  tags = var.tags

  response_export_values = [
    "properties.endpoint",
    "identity.principalId",
  ]
}

# ── AI Foundry Project ─────────────────────────────────────────
#
# CognitiveServices/accounts/projects — a CHILD resource of the account.
# This replaces the legacy azurerm_ai_foundry_project which created
# MachineLearningServices/workspaces (kind=Project).

resource "azapi_resource" "ai_foundry_project" {
  type                      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name                      = "proj-${var.name}"
  parent_id                 = azapi_resource.ai_foundry_account.id
  location                  = var.location
  schema_validation_enabled = false

  body = {
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }
    properties = {
      displayName = "proj-${var.name}"
      description = "AI Foundry project for ${var.name}"
    }
  }

  tags = var.tags

  response_export_values = [
    "identity.principalId",
    "properties.internalId",
  ]
}

# ── Model Deployments (on the AI Foundry account) ───────────────
#
# Models are deployed directly on the AI Services account, NOT on a
# separate OpenAI resource. The project inherits access to these models.

resource "azurerm_cognitive_deployment" "this" {
  for_each = { for d in var.model_deployments : d.name => d }

  name                 = each.value.name
  cognitive_account_id = azapi_resource.ai_foundry_account.id

  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.model_version
  }

  sku {
    name     = each.value.sku_name
    capacity = each.value.sku_capacity
  }

  # Note: capacity is managed by Terraform — do not add ignore_changes
}

# ── RBAC — Azure AI User for backend identity on the project ────
#
# Required for the backend to create/edit agents via the SDK.

resource "azurerm_role_assignment" "backend_ai_user" {
  count                = var.backend_identity_principal_id != "" ? 1 : 0
  scope                = azapi_resource.ai_foundry_project.id
  role_definition_name = "Azure AI User"
  principal_id         = var.backend_identity_principal_id
}

# ── RBAC — Cognitive Services OpenAI User on the account ────────
#
# Required for model inference calls (chat completions, etc.)

resource "azurerm_role_assignment" "backend_cognitive_user" {
  count                = var.backend_identity_principal_id != "" ? 1 : 0
  scope                = azapi_resource.ai_foundry_account.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.backend_identity_principal_id
}

# ── Outputs ─────────────────────────────────────────────────────

output "ai_services_id" {
  description = "AI Services account resource ID"
  value       = azapi_resource.ai_foundry_account.id
}

output "ai_services_endpoint" {
  description = "AI Services endpoint (services.ai.azure.com)"
  value       = azapi_resource.ai_foundry_account.output.properties.endpoint
}

output "hub_id" {
  description = "AI Foundry account ID (replaces legacy hub_id for interface compat)"
  value       = azapi_resource.ai_foundry_account.id
}

output "project_id" {
  description = "AI Foundry project resource ID"
  value       = azapi_resource.ai_foundry_project.id
}

output "project_endpoint" {
  description = "AI Foundry project endpoint for the agent SDK (FOUNDRY_PROJECT_ENDPOINT). Includes /api/projects/ path required by azure-ai-projects v1.x SDK."
  value       = "https://ais-${var.name}.services.ai.azure.com/api/projects/proj-${var.name}"
}

output "project_internal_id" {
  description = "Internal ID (GUID) of the project, needed for standard setup data-plane RBAC"
  value       = azapi_resource.ai_foundry_project.output.properties.internalId
}

output "account_principal_id" {
  description = "System-assigned managed identity principal ID of the AI Foundry account"
  value       = azapi_resource.ai_foundry_account.output.identity.principalId
}

output "project_principal_id" {
  description = "System-assigned managed identity principal ID of the AI Foundry project"
  value       = azapi_resource.ai_foundry_project.output.identity.principalId
}
