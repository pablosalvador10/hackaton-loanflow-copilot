# ═══════════════════════════════════════════════════════════════════
#  VIN Insight — Terraform Outputs
# ═══════════════════════════════════════════════════════════════════
#
#  Outputs are consumed by:
#    - azd (auto-reads ALLCAPS outputs into azd env)
#    - postprovision.sh (generates .env.azure files)
# ═══════════════════════════════════════════════════════════════════

# ── Resource Group ──────────────────────────────────────────────

output "AZURE_RESOURCE_GROUP_NAME" {
  description = "Resource group name"
  value       = azurerm_resource_group.rg.name
}

output "AZURE_LOCATION" {
  description = "Azure region"
  value       = azurerm_resource_group.rg.location
}

# ── Container Registry ──────────────────────────────────────────

output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  description = "ACR login server"
  value       = module.acr.login_server
}

output "AZURE_CONTAINER_REGISTRY_ENDPOINT" {
  description = "ACR endpoint (used by azd deploy)"
  value       = module.acr.login_server
}

output "AZURE_CONTAINER_REGISTRY_NAME" {
  description = "ACR name"
  value       = module.acr.name
}

# ── Container Apps ──────────────────────────────────────────────

output "AZURE_CONTAINER_APPS_ENVIRONMENT_ID" {
  description = "Container Apps Environment ID"
  value       = module.cae.id
}

output "SERVICE_BACKEND_URI" {
  description = "Backend container app URL"
  value       = module.backend.uri
}

output "SERVICE_FRONTEND_URI" {
  description = "Frontend container app URL"
  value       = module.frontend.uri
}

output "SERVICE_BACKEND_NAME" {
  description = "Backend container app name"
  value       = module.backend.name
}

output "SERVICE_FRONTEND_NAME" {
  description = "Frontend container app name"
  value       = module.frontend.name
}

# ── Cosmos DB ───────────────────────────────────────────────────

output "AZURE_COSMOS_ENDPOINT" {
  description = "Cosmos DB endpoint"
  value       = var.enable_cosmos_db ? module.cosmos[0].endpoint : ""
}

output "AZURE_COSMOS_DATABASE_NAME" {
  description = "Cosmos DB database name"
  value       = var.enable_cosmos_db ? module.cosmos[0].database_name : ""
}

# ── Azure OpenAI ────────────────────────────────────────────────

output "AZURE_OPENAI_ENDPOINT" {
  description = "Azure OpenAI endpoint"
  value       = var.enable_openai ? module.openai[0].endpoint : ""
}

output "AZURE_OPENAI_DEPLOYMENT_FULL" {
  description = "Azure OpenAI deployment name — GPT-4.1 (most capable)"
  value       = var.enable_openai ? "gpt-4-1" : ""
}

output "AZURE_OPENAI_API_VERSION" {
  description = "Azure OpenAI API version"
  value       = "2025-03-01-preview"
}

# ── AI Foundry ──────────────────────────────────────────────────

output "AZURE_AI_SERVICES_ENDPOINT" {
  description = "Azure AI Services endpoint (Foundry)"
  value       = var.enable_ai_foundry ? module.ai_foundry[0].ai_services_endpoint : ""
}

output "AZURE_AI_FOUNDRY_PROJECT_ENDPOINT" {
  description = "AI Foundry project endpoint for agent SDK (FOUNDRY_PROJECT_ENDPOINT)"
  value       = var.enable_ai_foundry ? module.ai_foundry[0].project_endpoint : ""
}

# ── Managed Identity ────────────────────────────────────────────

output "AZURE_MANAGED_IDENTITY_ID" {
  description = "Backend managed identity resource ID"
  value       = azurerm_user_assigned_identity.backend.id
}

output "AZURE_MANAGED_IDENTITY_CLIENT_ID" {
  description = "Backend managed identity client ID"
  value       = azurerm_user_assigned_identity.backend.client_id
}

# ── Observability ───────────────────────────────────────────────

output "AZURE_APPINSIGHTS_CONNECTION_STRING" {
  description = "Application Insights connection string"
  value       = module.appinsights.connection_string
  sensitive   = true
}

# ── Key Vault ───────────────────────────────────────────────────

output "AZURE_KEY_VAULT_URI" {
  description = "Key Vault URI"
  value       = var.enable_key_vault ? module.keyvault[0].uri : ""
}

output "AZURE_KEY_VAULT_NAME" {
  description = "Key Vault name"
  value       = var.enable_key_vault ? module.keyvault[0].name : ""
}
