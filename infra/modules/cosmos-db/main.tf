# ═══════════════════════════════════════════════════════════════════
#  Cosmos DB Module — NoSQL with Vector Search
# ═══════════════════════════════════════════════════════════════════

variable "name" {
  description = "Cosmos DB account name (globally unique, lowercase)"
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

variable "database_name" {
  description = "SQL database name"
  type        = string
  default     = "contoso-router"
}

variable "containers" {
  description = "List of SQL containers to create"
  type = list(object({
    name               = string
    partition_key_path = string
    throughput         = optional(number, 400)
    default_ttl        = optional(number)
    # Vector search: embedding dimensions, index type, distance function
    vector_dimensions = optional(number)
    vector_path       = optional(string)
    vector_index_type = optional(string, "quantizedFlat")
    vector_distance   = optional(string, "cosine")
  }))
}

variable "total_throughput_limit" {
  description = "Account-level total throughput cap (RU/s)"
  type        = number
  default     = 4000
}

variable "role_assignment_principal_ids" {
  description = "Principal IDs to grant the custom data-plane read/write role"
  type        = list(string)
  default     = []
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID for private endpoint (empty = public access)"
  type        = string
  default     = ""
}

variable "enable_private_endpoint" {
  description = "Whether to create private endpoint resources (must be known at plan time)"
  type        = bool
  default     = false
}

variable "virtual_network_id" {
  description = "VNet ID for private DNS zone link (required when private_endpoint_subnet_id is set)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# ── Locals ──────────────────────────────────────────────────────

locals {
  # Containers that have vector search enabled
  vector_containers = [for c in var.containers : c if c.vector_dimensions != null]
}

# ── Cosmos DB Account ───────────────────────────────────────────

resource "azurerm_cosmosdb_account" "this" {
  name                          = var.name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  local_authentication_disabled = true # Key auth disabled by policy
  public_network_access_enabled = !var.enable_private_endpoint
  tags                          = var.tags

  consistency_policy {
    consistency_level = "Session"
  }

  capacity {
    total_throughput_limit = var.total_throughput_limit
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  # Enable vector search capability for NoSQL API
  dynamic "capabilities" {
    for_each = length(local.vector_containers) > 0 ? [1] : []
    content {
      name = "EnableNoSQLVectorSearch"
    }
  }
}

# ── Database ────────────────────────────────────────────────────

resource "azurerm_cosmosdb_sql_database" "this" {
  name                = var.database_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
}

# ── Containers (standard — no vector search) ────────────────────

resource "azurerm_cosmosdb_sql_container" "standard" {
  for_each            = { for c in var.containers : c.name => c if c.vector_dimensions == null }
  name                = each.value.name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.this.name
  partition_key_paths = [each.value.partition_key_path]
  throughput          = each.value.throughput
  default_ttl         = each.value.default_ttl
}

# ── Containers (vector search enabled) ──────────────────────────
# Vector search containers require indexing_policy and vector_embedding_policy
# which are set via the azurerm provider.

resource "azurerm_cosmosdb_sql_container" "vector" {
  for_each            = { for c in var.containers : c.name => c if c.vector_dimensions != null }
  name                = each.value.name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.this.name
  partition_key_paths = [each.value.partition_key_path]
  throughput          = each.value.throughput
  default_ttl         = each.value.default_ttl

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    # Exclude the vector embedding path from the standard index
    excluded_path {
      path = each.value.vector_path != null ? "${each.value.vector_path}/*" : "/_vector/*"
    }
  }
}

# ── RBAC — Custom data-plane role ───────────────────────────────

resource "azurerm_cosmosdb_sql_role_definition" "readwrite" {
  name                = "${var.name}-readwrite"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  type                = "CustomRole"
  assignable_scopes   = [azurerm_cosmosdb_account.this.id]

  permissions {
    data_actions = [
      "Microsoft.DocumentDB/databaseAccounts/readMetadata",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/executeQuery",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/readChangeFeed",
    ]
  }
}

resource "azurerm_cosmosdb_sql_role_assignment" "this" {
  count               = length(var.role_assignment_principal_ids)
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.readwrite.id
  principal_id        = var.role_assignment_principal_ids[count.index]
  scope               = azurerm_cosmosdb_account.this.id
}

# ── Private Endpoint ────────────────────────────────────────────

resource "azurerm_private_endpoint" "this" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "pe-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "cosmos-connection"
    private_connection_resource_id = azurerm_cosmosdb_account.this.id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }

  private_dns_zone_group {
    name                 = "cosmos-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.this[0].id]
  }
}

resource "azurerm_private_dns_zone" "this" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "privatelink.documents.azure.com"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  count                 = var.enable_private_endpoint ? 1 : 0
  name                  = "cosmos-vnet-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.this[0].name
  virtual_network_id    = var.virtual_network_id
}

# ── Outputs ─────────────────────────────────────────────────────

output "id" {
  value = azurerm_cosmosdb_account.this.id
}

output "endpoint" {
  value = azurerm_cosmosdb_account.this.endpoint
}

output "database_name" {
  value = azurerm_cosmosdb_sql_database.this.name
}

output "account_name" {
  value = azurerm_cosmosdb_account.this.name
}
