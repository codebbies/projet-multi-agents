terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }
}

provider "azurerm" {
  features {}
}

# ===========================================================
# RESSOURCES PERSISTANTES
# Ne jamais détruire entre deux sessions de travail :
# soit elles ne coûtent presque rien à laisser tourner,
# soit elles contiennent des données qu'on ne veut pas perdre.
# ===========================================================

resource "azurerm_resource_group" "projet" {
  name     = "rg-transport-carbone"
  location = "francecentral"
}

# --- Azure OpenAI : facturé au token consommé, pas à l'heure
#     d'existence -> aucun intérêt à le détruire entre 2 sessions.
resource "azurerm_cognitive_account" "openai" {
  name                = "openai-transport-carbone"
  resource_group_name = azurerm_resource_group.projet.name
  location            = azurerm_resource_group.projet.location
  kind                = "OpenAI"
  sku_name            = "S0"
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }
  sku {
    name     = "Standard"
    capacity = 10
  }
}

# --- SQL Database : contient l'historique des requêtes.
#     La détruire = perdre cet historique à chaque session.
resource "azurerm_mssql_server" "sql" {
  name                         = "sql-transport-carbone"
  resource_group_name          = azurerm_resource_group.projet.name
  location                     = azurerm_resource_group.projet.location
  version                      = "12.0"
  administrator_login          = var.sql_admin_login
  administrator_login_password = var.sql_admin_password
}

resource "azurerm_mssql_database" "historique" {
  name        = "db-historique-requetes"
  server_id   = azurerm_mssql_server.sql.id
  sku_name    = "Basic" # 5 DTU, 2 Go — cf. tableau de coûts, $6.11/mois
  max_size_gb = 2
}

# --- Storage Account : contient les vrais fichiers de rapports
#     générés. La détruire = perdre les rapports eux-mêmes.
resource "azurerm_storage_account" "rapports" {
  name                      = "strapportstc"
  resource_group_name       = azurerm_resource_group.projet.name
  location                  = azurerm_resource_group.projet.location
  account_tier              = "Standard"
  account_replication_type  = "LRS"
  access_tier               = "Hot"
}

output "resource_group_name" {
  value       = azurerm_resource_group.projet.name
  description = "Utilisé par les ressources éphémères pour retrouver ce groupe"
}