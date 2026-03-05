terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.5"
    }
  }
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
}

provider "azapi" {}
