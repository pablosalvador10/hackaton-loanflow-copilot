# ═══════════════════════════════════════════════════════════════════
#  VIN Insight — Input Variables
# ═══════════════════════════════════════════════════════════════════

# ── Core ─────────────────────────────────────────────────────────

variable "environment_name" {
  description = "Name of the azd environment (used for resource naming)"
  type        = string

  validation {
    condition     = length(var.environment_name) >= 3 && length(var.environment_name) <= 24
    error_message = "environment_name must be 3-24 characters."
  }
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "vin-insight-rg"
}

variable "tags" {
  description = "Additional tags applied to all resources"
  type        = map(string)
  default     = {}
}

# ── Service Images ──────────────────────────────────────────────

variable "backend_image_name" {
  description = "Backend container image name (set by azd deploy)"
  type        = string
  default     = ""
}

variable "frontend_image_name" {
  description = "Frontend container image name (set by azd deploy)"
  type        = string
  default     = ""
}

# ── Feature Flags ───────────────────────────────────────────────

variable "enable_cosmos_db" {
  description = "Provision Cosmos DB (disable for local-only dev with STORAGE_MODE=inmemory)"
  type        = bool
  default     = true
}

variable "enable_openai" {
  description = "Provision Azure OpenAI (disable to use mock mode)"
  type        = bool
  default     = true
}

variable "enable_ai_foundry" {
  description = "Provision AI Foundry project (requires storage account with shared key access)"
  type        = bool
  default     = true
}

variable "enable_key_vault" {
  description = "Provision Key Vault for secrets management (required by AI Foundry)"
  type        = bool
  default     = true
}

# ── Cosmos DB ───────────────────────────────────────────────────

variable "cosmos_database_name" {
  description = "Cosmos DB database name"
  type        = string
  default     = "vin-insight"
}

variable "cosmos_throughput_limit" {
  description = "Cosmos DB total account throughput limit (RU/s)"
  type        = number
  default     = 4000
}

# ── Azure OpenAI ────────────────────────────────────────────────

variable "openai_models" {
  description = "OpenAI model deployments to create"
  type = list(object({
    deployment_name = string
    model_name      = string
    model_version   = string
    sku_name        = optional(string, "Standard")
    sku_capacity    = optional(number, 150)
  }))
  default = [
    {
      deployment_name = "gpt-4-1-nano"
      model_name      = "gpt-4.1-nano"
      model_version   = "2025-04-14"
      sku_name        = "GlobalStandard"
      sku_capacity    = 150
    },
    {
      deployment_name = "gpt-4-1-mini"
      model_name      = "gpt-4.1-mini"
      model_version   = "2025-04-14"
      sku_name        = "GlobalStandard"
      sku_capacity    = 150
    },
    {
      deployment_name = "gpt-4-1"
      model_name      = "gpt-4.1"
      model_version   = "2025-04-14"
      sku_name        = "GlobalStandard"
      sku_capacity    = 150
    },
  ]
}

# ── Container Apps ──────────────────────────────────────────────

variable "backend_cpu" {
  description = "Backend container CPU cores"
  type        = number
  default     = 0.5
}

variable "backend_memory" {
  description = "Backend container memory"
  type        = string
  default     = "1Gi"
}

variable "backend_min_replicas" {
  description = "Backend minimum replicas"
  type        = number
  default     = 1
}

variable "backend_max_replicas" {
  description = "Backend maximum replicas"
  type        = number
  default     = 5
}

variable "frontend_cpu" {
  description = "Frontend container CPU cores"
  type        = number
  default     = 0.25
}

variable "frontend_memory" {
  description = "Frontend container memory"
  type        = string
  default     = "0.5Gi"
}

variable "frontend_min_replicas" {
  description = "Frontend minimum replicas"
  type        = number
  default     = 1
}

variable "frontend_max_replicas" {
  description = "Frontend maximum replicas"
  type        = number
  default     = 3
}

# ── CORS ────────────────────────────────────────────────────────

variable "cors_origins" {
  description = "Allowed CORS origins for the backend (set by postprovision)"
  type        = string
  default     = ""

  validation {
    condition     = var.cors_origins != "*"
    error_message = "CORS origin '*' is not allowed. Specify explicit origins."
  }
}

# ── Observability ───────────────────────────────────────────────

variable "log_retention_days" {
  description = "Log Analytics retention in days"
  type        = number
  default     = 30
}
