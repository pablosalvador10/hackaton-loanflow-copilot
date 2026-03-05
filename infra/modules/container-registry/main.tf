# ── Variables ────────────────────────────────────────────────────
variable "name" {
  description = "Container registry name (alphanumeric only, globally unique)"
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

variable "sku" {
  description = "ACR SKU (Basic, Standard, Premium)"
  type        = string
  default     = "Basic"
}

variable "admin_enabled" {
  description = "Enable admin user (not recommended for production — use managed identity pull)"
  type        = bool
  default     = false
}

variable "pull_identity_principal_ids" {
  description = "Principal IDs to grant AcrPull role"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# ── Resource ─────────────────────────────────────────────────────
resource "azurerm_container_registry" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.sku
  admin_enabled       = var.admin_enabled
  tags                = var.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  count                = length(var.pull_identity_principal_ids)
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = var.pull_identity_principal_ids[count.index]
}

# ── Outputs ──────────────────────────────────────────────────────
output "id" {
  value = azurerm_container_registry.this.id
}

output "name" {
  value = azurerm_container_registry.this.name
}

output "login_server" {
  value = azurerm_container_registry.this.login_server
}

output "admin_username" {
  value     = azurerm_container_registry.this.admin_username
  sensitive = true
}

output "admin_password" {
  value     = azurerm_container_registry.this.admin_password
  sensitive = true
}
