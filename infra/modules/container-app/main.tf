# ── Variables ────────────────────────────────────────────────────
variable "name" {
  description = "Container app name"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "container_app_environment_id" {
  description = "Container Apps Environment resource ID"
  type        = string
}

variable "revision_mode" {
  description = "Revision mode (Single or Multiple)"
  type        = string
  default     = "Single"
}

variable "image_name" {
  description = "Container image name (e.g. myapp:latest)"
  type        = string
}

variable "container_registry_login_server" {
  description = "ACR login server (e.g. myacr.azurecr.io)"
  type        = string
}

variable "registry_identity_id" {
  description = "User-assigned identity resource ID for ACR pull (leave empty to skip registry config)"
  type        = string
  default     = ""
}

variable "target_port" {
  description = "Container port to expose"
  type        = number
}

variable "cpu" {
  description = "CPU cores (e.g. 0.5)"
  type        = number
  default     = 0.5
}

variable "memory" {
  description = "Memory allocation (e.g. 1Gi)"
  type        = string
  default     = "1Gi"
}

variable "min_replicas" {
  description = "Minimum replica count"
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum replica count"
  type        = number
  default     = 3
}

variable "external_ingress" {
  description = "Enable external (internet-facing) ingress"
  type        = bool
  default     = true
}

variable "env_vars" {
  description = "Non-secret environment variables"
  type = list(object({
    name        = string
    value       = optional(string)
    secret_name = optional(string)
  }))
  default = []
}

variable "secrets" {
  description = "Secret values (referenced by env_vars via secret_name)"
  type = list(object({
    name  = string
    value = string
  }))
  default   = []
  sensitive = true
}

variable "health_check_path" {
  description = "HTTP path for health probes"
  type        = string
  default     = "/healthz"
}

variable "identity_ids" {
  description = "User-assigned managed identity resource IDs to attach"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# ── Resource ─────────────────────────────────────────────────────
resource "azurerm_container_app" "this" {
  name                         = var.name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  revision_mode                = var.revision_mode
  workload_profile_name        = "Consumption"
  tags                         = var.tags

  identity {
    type         = length(var.identity_ids) > 0 ? "UserAssigned" : "None"
    identity_ids = var.identity_ids
  }

  dynamic "registry" {
    for_each = var.registry_identity_id != "" ? [1] : []
    content {
      server   = var.container_registry_login_server
      identity = var.registry_identity_id
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = var.name
      image  = can(regex("\\.", var.image_name)) ? var.image_name : "${var.container_registry_login_server}/${var.image_name}"
      cpu    = var.cpu
      memory = var.memory

      dynamic "env" {
        for_each = var.env_vars
        content {
          name        = env.value.name
          value       = env.value.secret_name == null ? env.value.value : null
          secret_name = env.value.secret_name
        }
      }

      liveness_probe {
        path             = var.health_check_path
        port             = var.target_port
        transport        = "HTTP"
        initial_delay    = 10
        interval_seconds = 30
      }

      readiness_probe {
        path             = var.health_check_path
        port             = var.target_port
        transport        = "HTTP"
        initial_delay    = 5
        interval_seconds = 10
      }

      startup_probe {
        path                    = var.health_check_path
        port                    = var.target_port
        transport               = "HTTP"
        initial_delay           = 3
        interval_seconds        = 5
        failure_count_threshold = 10
      }
    }
  }

  ingress {
    external_enabled = var.external_ingress
    target_port      = var.target_port
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  dynamic "secret" {
    for_each = var.secrets
    content {
      name  = secret.value.name
      value = secret.value.value
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].container[0].image,
    ]
  }
}

# ── Outputs ──────────────────────────────────────────────────────
output "id" {
  value = azurerm_container_app.this.id
}

output "name" {
  value = azurerm_container_app.this.name
}

output "fqdn" {
  value = azurerm_container_app.this.ingress[0].fqdn
}

output "uri" {
  value = "https://${azurerm_container_app.this.ingress[0].fqdn}"
}
