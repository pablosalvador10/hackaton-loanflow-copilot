# ── Variables ────────────────────────────────────────────────────
variable "name" {
  description = "Container Apps Environment name"
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

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  type        = string
}

variable "infrastructure_subnet_id" {
  description = "Subnet ID for VNet injection (must be /23 or larger, delegated to Microsoft.App/environments)"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# ── Resource ─────────────────────────────────────────────────────
resource "azurerm_container_app_environment" "this" {
  name                       = var.name
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  infrastructure_subnet_id   = var.infrastructure_subnet_id
  tags                       = var.tags

  # Explicitly declare the default Consumption workload profile that Azure adds
  # automatically. This keeps it fully tracked by Terraform.
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }

  lifecycle {
    ignore_changes = [
      # Azure auto-generates this managed resource group name (e.g. "ME_cae-xxx_rg_region").
      # It's a ForceNew attribute — if we don't pin it, Terraform sees state ≠ config
      # and destroys+recreates the entire CAE on every apply.
      infrastructure_resource_group_name,
    ]
  }
}

# ── Outputs ──────────────────────────────────────────────────────
output "id" {
  value = azurerm_container_app_environment.this.id
}

output "default_domain" {
  value = azurerm_container_app_environment.this.default_domain
}

output "static_ip_address" {
  value = azurerm_container_app_environment.this.static_ip_address
}
