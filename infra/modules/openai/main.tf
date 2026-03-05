# ═══════════════════════════════════════════════════════════════════
#  Azure OpenAI Module — Multi-model deployments
# ═══════════════════════════════════════════════════════════════════

variable "name" {
  description = "Azure OpenAI resource name (also used as custom subdomain)"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "sku_name" {
  description = "Cognitive Services SKU"
  type        = string
  default     = "S0"
}

variable "model_deployments" {
  description = "List of model deployments to create"
  type = list(object({
    name          = string
    model_name    = string
    model_version = string
    sku_name      = optional(string, "Standard")
    sku_capacity  = optional(number, 150)
  }))
  default = []
}

variable "cognitive_services_user_principal_ids" {
  description = "Principal IDs to grant Cognitive Services OpenAI User role"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# ── OpenAI Account ──────────────────────────────────────────────

resource "azurerm_cognitive_account" "this" {
  name                  = var.name
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "OpenAI"
  sku_name              = var.sku_name
  custom_subdomain_name = var.name
  local_auth_enabled    = false # Azure policy enforces this
  tags                  = var.tags
}

# ── Model Deployments ───────────────────────────────────────────

resource "azurerm_cognitive_deployment" "this" {
  for_each             = { for d in var.model_deployments : d.name => d }
  name                 = each.value.name
  cognitive_account_id = azurerm_cognitive_account.this.id

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

# ── RBAC ────────────────────────────────────────────────────────

resource "azurerm_role_assignment" "cognitive_user" {
  count                = length(var.cognitive_services_user_principal_ids)
  scope                = azurerm_cognitive_account.this.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.cognitive_services_user_principal_ids[count.index]
}

# ── Outputs ─────────────────────────────────────────────────────

output "id" {
  value = azurerm_cognitive_account.this.id
}

output "endpoint" {
  value = azurerm_cognitive_account.this.endpoint
}

output "name" {
  value = azurerm_cognitive_account.this.name
}

output "deployment_names" {
  description = "Map of deployment key → deployment name"
  value       = { for k, v in azurerm_cognitive_deployment.this : k => v.name }
}
