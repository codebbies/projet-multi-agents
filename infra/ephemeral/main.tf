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
# RESSOURCES ÉPHÉMÈRES
# À créer avec `terraform apply` en arrivant, à supprimer avec
# `terraform destroy` en partant. Aucune donnée persistante
# n'est stockée ici -> rien à perdre en les détruisant.
# ===========================================================

# Le groupe de ressources est créé par le dossier "persistent/",
# on le récupère ici plutôt que d'en recréer un.
data "azurerm_resource_group" "projet" {
  name = "rg-transport-carbone"
}

# --- App Service (dashboard Streamlit) — LINUX, pas Windows.
#     Streamlit est du Python pur, aucune fonctionnalité perdue
#     en Linux, et le coût passe de $68.62/mois (Windows, facturé
#     en continu 24/7) à environ $13.14/mois (Linux) —
#     et à quasi $0 en pratique puisque cette ressource n'existe
#     que pendant les sessions actives (cf. workflow GitHub Actions).
resource "azurerm_service_plan" "plan" {
  name                = "asp-streamlit"
  resource_group_name = data.azurerm_resource_group.projet.name
  location            = data.azurerm_resource_group.projet.location
  os_type             = "Linux"
  sku_name            = "B1"
}

resource "azurerm_linux_web_app" "streamlit" {
  name                = "app-streamlit-transport-carbone"
  resource_group_name = data.azurerm_resource_group.projet.name
  location            = data.azurerm_resource_group.projet.location
  service_plan_id     = azurerm_service_plan.plan.id

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }
}

# --- Cache Redis (résultats récents) — remplaçable sans risque :
#     un cache videé se reconstitue tout seul au fil de l'usage.
resource "azurerm_redis_cache" "cache" {
  name                  = "redis-transport-carbone"
  resource_group_name   = data.azurerm_resource_group.projet.name
  location              = data.azurerm_resource_group.projet.location
  capacity              = 0 # C0
  family                = "C"
  sku_name              = "Basic"
  non_ssl_port_enabled  = false
}

# --- Sandbox Docker (exécution de l'Exécuteur) — déjà optimisé
#     par nature : ne tourne que pendant l'exécution réelle du
#     code, pas besoin de le mettre dans le cycle apply/destroy.
resource "azurerm_container_group" "sandbox_docker" {
  name                = "aci-sandbox-executeur"
  resource_group_name = data.azurerm_resource_group.projet.name
  location            = data.azurerm_resource_group.projet.location
  os_type             = "Windows"
  restart_policy      = "Never"

  container {
    name   = "sandbox"
    image  = "mcr.microsoft.com/windows/nanoserver:ltsc2022"
    cpu    = "2"
    memory = "4"
  }
}
