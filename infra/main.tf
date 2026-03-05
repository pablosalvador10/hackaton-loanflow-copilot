# ═══════════════════════════════════════════════════════════════════
#  VIN Insight — Root Terraform Module
# ═══════════════════════════════════════════════════════════════════
#
#  Services provisioned:
#    - Resource Group
#    - VNet + Subnet (ACA)
#    - Log Analytics + Application Insights
#    - Azure Container Registry (ACR)
#    - User-Assigned Managed Identity
#    - Container Apps Environment (VNet-injected)
#    - Container Apps (Backend + Frontend)
#    - Cosmos DB (NoSQL) — claims, vin_lookups, conversations
#    - Azure OpenAI with model deployments
#    - AI Foundry (Hub + Project)
#    - Key Vault (RBAC-based)
#
# ═══════════════════════════════════════════════════════════════════

# ── Data Sources ─────────────────────────────────────────────────
data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

# ── Locals ───────────────────────────────────────────────────────
locals {
  # Unique suffix derived from environment + subscription (stable, deterministic)
  resource_suffix = substr(sha256("${var.environment_name}-${data.azurerm_subscription.current.subscription_id}"), 0, 6)

  tags = merge(var.tags, {
    "azd-env-name" = var.environment_name
    "project"      = "vin-insight"
    "managed-by"   = "terraform"
  })

  # Centralized resource naming
  resource_names = {
    rg       = var.resource_group_name
    vnet     = "vnet-${var.environment_name}"
    log      = "log-${var.environment_name}"
    appi     = "appi-${var.environment_name}"
    acr      = "acr${replace(var.environment_name, "-", "")}${local.resource_suffix}"
    cae      = "cae-${var.environment_name}"
    cosmos   = "cosmos-${var.environment_name}-${local.resource_suffix}"
    openai   = "oai-${var.environment_name}-${local.resource_suffix}"
    aifndry  = "aif-${var.environment_name}-${local.resource_suffix}"
    kv       = "kv-${substr(var.environment_name, 0, 14)}-${local.resource_suffix}"
    mi       = "id-${var.environment_name}-backend"
    backend  = "ca-backend-${var.environment_name}"
    frontend = "ca-frontend-${var.environment_name}"
  }

  # Default images (mcr placeholder until first azd deploy)
  backend_image  = var.backend_image_name != "" ? var.backend_image_name : "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
  frontend_image = var.frontend_image_name != "" ? var.frontend_image_name : "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

# ── Resource Group ───────────────────────────────────────────────
resource "azurerm_resource_group" "rg" {
  name     = local.resource_names.rg
  location = var.location
  tags     = local.tags
}

# ═══════════════════════════════════════════════════════════════════
#  NETWORKING
# ═══════════════════════════════════════════════════════════════════

resource "azurerm_virtual_network" "vnet" {
  name                = local.resource_names.vnet
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["10.0.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "aca" {
  name                 = "snet-aca"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.0.0/23"]

  delegation {
    name = "aca-delegation"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# ═══════════════════════════════════════════════════════════════════
#  IDENTITY
# ═══════════════════════════════════════════════════════════════════

resource "azurerm_user_assigned_identity" "backend" {
  name                = local.resource_names.mi
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.tags
}

# ═══════════════════════════════════════════════════════════════════
#  OBSERVABILITY
# ═══════════════════════════════════════════════════════════════════

module "logs" {
  source              = "./modules/log-analytics"
  name                = local.resource_names.log
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  retention_in_days   = var.log_retention_days
  tags                = local.tags
}

module "appinsights" {
  source              = "./modules/application-insights"
  name                = local.resource_names.appi
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  workspace_id        = module.logs.id
  tags                = local.tags
}

# ═══════════════════════════════════════════════════════════════════
#  CONTAINER REGISTRY
# ═══════════════════════════════════════════════════════════════════

module "acr" {
  source              = "./modules/container-registry"
  name                = local.resource_names.acr
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.tags

  pull_identity_principal_ids = [
    azurerm_user_assigned_identity.backend.principal_id,
  ]
}

# ═══════════════════════════════════════════════════════════════════
#  CONTAINER APPS ENVIRONMENT (VNet-injected)
# ═══════════════════════════════════════════════════════════════════

module "cae" {
  source                     = "./modules/container-apps-environment"
  name                       = local.resource_names.cae
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  log_analytics_workspace_id = module.logs.id
  infrastructure_subnet_id   = azurerm_subnet.aca.id
  tags                       = local.tags
}

# ═══════════════════════════════════════════════════════════════════
#  COSMOS DB (NoSQL) — claims, vin_lookups, conversations
# ═══════════════════════════════════════════════════════════════════

module "cosmos" {
  count  = var.enable_cosmos_db ? 1 : 0
  source = "./modules/cosmos-db"

  name                   = local.resource_names.cosmos
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  database_name          = var.cosmos_database_name
  total_throughput_limit = var.cosmos_throughput_limit
  tags                   = local.tags

  containers = [
    {
      name               = "claims"
      partition_key_path = "/claim_id"
      throughput         = 400
    },
    {
      name               = "vin_lookups"
      partition_key_path = "/vin"
      throughput         = 400
    },
    {
      name               = "conversations"
      partition_key_path = "/conversation_id"
      throughput         = 400
    },
  ]

  role_assignment_principal_ids = [
    azurerm_user_assigned_identity.backend.principal_id,
  ]

  # No private endpoint for now — simplifies local dev
  enable_private_endpoint = false
}

# ═══════════════════════════════════════════════════════════════════
#  AZURE OPENAI (model deployments for Foundry)
# ═══════════════════════════════════════════════════════════════════

module "openai" {
  count  = var.enable_openai ? 1 : 0
  source = "./modules/openai"

  name                = local.resource_names.openai
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.tags

  model_deployments = [
    for m in var.openai_models : {
      name          = m.deployment_name
      model_name    = m.model_name
      model_version = m.model_version
      sku_name      = m.sku_name
      sku_capacity  = m.sku_capacity
    }
  ]

  cognitive_services_user_principal_ids = [
    azurerm_user_assigned_identity.backend.principal_id,
  ]
}

# ═══════════════════════════════════════════════════════════════════
#  AI FOUNDRY (Account + Project — New Foundry Model)
# ═══════════════════════════════════════════════════════════════════

module "ai_foundry" {
  count  = var.enable_ai_foundry ? 1 : 0
  source = "./modules/ai-foundry"

  name                    = local.resource_names.aifndry
  resource_group_name     = azurerm_resource_group.rg.name
  resource_group_id       = azurerm_resource_group.rg.id
  location                = azurerm_resource_group.rg.location
  application_insights_id = module.appinsights.id
  key_vault_id            = var.enable_key_vault ? module.keyvault[0].id : ""
  tags                    = local.tags

  backend_identity_principal_id = azurerm_user_assigned_identity.backend.principal_id

  # Deploy models directly on the AI Services account (required for Agents API)
  model_deployments = [
    for m in var.openai_models : {
      name          = m.deployment_name
      model_name    = m.model_name
      model_version = m.model_version
      sku_name      = m.sku_name
      sku_capacity  = m.sku_capacity
    }
  ]
}

# ═══════════════════════════════════════════════════════════════════
#  KEY VAULT
# ═══════════════════════════════════════════════════════════════════

module "keyvault" {
  count  = var.enable_key_vault ? 1 : 0
  source = "./modules/key-vault"

  name                = local.resource_names.kv
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  tags                = local.tags

  secrets_officer_principal_ids = [
    data.azurerm_client_config.current.object_id,
  ]

  secrets_reader_principal_ids = [
    azurerm_user_assigned_identity.backend.principal_id,
  ]
}

# ═══════════════════════════════════════════════════════════════════
#  CONTAINER APPS
# ═══════════════════════════════════════════════════════════════════

module "backend" {
  source = "./modules/container-app"

  name                            = local.resource_names.backend
  resource_group_name             = azurerm_resource_group.rg.name
  container_app_environment_id    = module.cae.id
  container_registry_login_server = module.acr.login_server
  registry_identity_id            = azurerm_user_assigned_identity.backend.id
  image_name                      = local.backend_image
  target_port                     = 8001
  cpu                             = var.backend_cpu
  memory                          = var.backend_memory
  min_replicas                    = var.backend_min_replicas
  max_replicas                    = var.backend_max_replicas
  external_ingress                = true
  health_check_path               = "/healthz"
  identity_ids                    = [azurerm_user_assigned_identity.backend.id]

  tags = merge(local.tags, {
    "azd-service-name" = "backend"
  })

  secrets = [
    {
      name  = "appinsights-connection-string"
      value = module.appinsights.connection_string
    },
  ]

  env_vars = concat(
    [
      # Foundry Agent
      { name = "FOUNDRY_PROJECT_ENDPOINT", value = var.enable_ai_foundry ? module.ai_foundry[0].project_endpoint : "" },
      { name = "FOUNDRY_MODEL_DEPLOYMENT_NAME", value = "gpt-4-1" },
      { name = "FOUNDRY_CREDENTIAL_MODE", value = "managed_identity" },
      # Cosmos DB
      { name = "STORAGE_MODE", value = var.enable_cosmos_db ? "cosmos" : "inmemory" },
      { name = "COSMOS_ENDPOINT", value = var.enable_cosmos_db ? module.cosmos[0].endpoint : "" },
      { name = "COSMOS_DATABASE_NAME", value = var.cosmos_database_name },
      # Server
      { name = "API_HOST", value = "0.0.0.0" },
      { name = "API_PORT", value = "8001" },
      { name = "LOG_LEVEL", value = "INFO" },
      # Observability
      { name = "OTEL_EXPORTER", value = "azure" },
      # Identity
      { name = "AZURE_CLIENT_ID", value = azurerm_user_assigned_identity.backend.client_id },
      # Observability (secret ref)
      { name = "APPLICATIONINSIGHTS_CONNECTION_STRING", secret_name = "appinsights-connection-string" },
    ],
    # CORS (set by postprovision script)
    var.cors_origins != "" ? [
      { name = "CORS_ORIGINS", value = var.cors_origins },
    ] : [],
  )
}

module "frontend" {
  source = "./modules/container-app"

  name                            = local.resource_names.frontend
  resource_group_name             = azurerm_resource_group.rg.name
  container_app_environment_id    = module.cae.id
  container_registry_login_server = module.acr.login_server
  registry_identity_id            = azurerm_user_assigned_identity.backend.id
  image_name                      = local.frontend_image
  target_port                     = 80
  cpu                             = var.frontend_cpu
  memory                          = var.frontend_memory
  min_replicas                    = var.frontend_min_replicas
  max_replicas                    = var.frontend_max_replicas
  external_ingress                = true
  health_check_path               = "/"
  identity_ids                    = [azurerm_user_assigned_identity.backend.id]

  tags = merge(local.tags, {
    "azd-service-name" = "frontend"
  })
}
