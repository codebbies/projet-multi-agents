# Pipeline Carbone Last-Mile

Système multi-agents (AutoGen + Azure OpenAI) qui calcule et compare l'empreinte
carbone de tournées de livraison du dernier kilomètre, sur des données réelles
Amazon Last-Mile Routing Research Challenge.

Stage Smartovate LTD. Architecture imposée par le cahier des charges : trois
agents (Planificateur → Exécuteur → Critique) qui collaborent, avec exécution
de code sécurisée en sandbox Docker.

## Architecture

- **Planificateur** — décompose une requête en langage naturel en plan
  numéroté, ne génère jamais de code (`agents/planner.py`)
- **Exécuteur** — écrit et exécute du code Python dans la sandbox Docker
  (`agents/executor.py`)
- **Critique** — vérifie le résultat de l'Exécuteur, approuve ou demande une
  correction, cycle borné à 6 tours (`agents/critic.py`, `agents/executor_critic_team.py`)
- **Debugger** — pipeline dédié pour corriger un script Python buggé fourni
  par l'utilisateur (`agents/debugger.py`, US 3.2)

Schéma d'architecture complet : voir la page Notion Sprint 2 (lien dans le
rapport de stage).

### Trois leviers de calcul carbone

| Levier | Résultat mesuré | Nature |
|---|---|---|
| Substitution de véhicule | jusqu'à -46% | Calcul exact (données déjà présentes) |
| TSP bas-carbone (réordonnancement des arrêts) | -6.11% | Calcul exact, algo testé séparément (`docker/executor/tsp_tools.py`) |
| Prédiction ML (route nouvelle, arrêts inconnus) | ~16.9 kg CO2e | Estimation (Random Forest, R²=0.51) |

## Prérequis

- Python 3.12+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — doit être **lancé** avant d'exécuter quoi que ce soit
- Un déploiement Azure OpenAI (modèle type `gpt-4.1-mini`)

## Installation

```bash
pip install -r requirements.txt
```

Copier `.env.example` en `.env` et renseigner les vraies valeurs :

```bash
cp .env.example .env
```

```
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://votre-ressource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini-test
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

Générer `OAI_CONFIG_LIST` (format AutoGen) à partir du `.env` :

```bash
python scripts/generate_oai_config_list.py
```

Valider la connexion Azure OpenAI :

```bash
python scripts/test_connexion.py
```

### Construire la sandbox Docker

```bash
cd docker/executor
docker build -t lastmile-executor:latest .
cd ../..
```

### Données

Les fichiers `data/gold/*.csv` (dim_route, dim_stop, dim_vehicle,
fact_route_leg) ne sont pas versionnés (trop volumineux) — récupérer depuis
Azure Blob et placer dans `data/gold/`. Point technique important : ces CSV
contiennent un vrai code d'arrêt `"NA"` — toujours lire avec
`pd.read_csv(path, keep_default_na=False, na_values=[''])`.

### Modèle de prédiction ML

Non versionné (reproductible), à entraîner une fois :

```bash
python scripts/train_carbon_predictor.py
```

## Lancer les tests

Docker Desktop doit être ouvert. Depuis `scripts/` :

```bash
python test_planner.py              # US 2.1
python test_executor.py             # US 2.2
python test_critic.py               # US 2.3
python test_vehicle_scenarios.py    # Levier 1 : substitution vehicule
python test_tsp.py                  # Levier 2 : TSP bas-carbone
python test_ml_prediction.py        # Levier 3 : prediction ML
python test_debugging.py            # US 3.2 : debugging automatique
python audit_star_schema.py         # Audit qualite des donnees gold
```

## Sécurité de la sandbox

Le code exécuté par l'agent Exécuteur (généré par un LLM, jamais relu par un
humain avant exécution) est confiné :

- Accès en **lecture seule** aux données et au modèle (`data/gold`, `models/`)
- **Aucun accès réseau** (le conteneur est déconnecté après démarrage, voir
  `scripts/executor_sandbox.py`)
- Utilisateur non-root dans le conteneur

## Structure du dépôt

```
agents/           agents AutoGen (planificateur, executeur, critique, debugger)
scripts/          scripts d'entrainement, de test, et utilitaires
docker/executor/  Dockerfile + outils de la sandbox (tsp_tools.py)
data/gold/        donnees gold (non versionnees, cf. section Donnees)
models/           modele ML entraine (non versionne, cf. section ci-dessus)
demo_backup/      deroule de demo + sorties de secours
infra/            Terraform (ressources Azure persistantes/ephemeres)
```

## Limites connues

- Système non déterministe (LLM) : ~80% de convergence observée sur les
  leviers testés ; le garde-fou anti-boucle (6 tours max) empêche un blocage
  indéfini
- Modèle de prédiction ML volontairement baseline (R²=0.51) — amélioration
  possible (plus de features, gradient boosting) mais pas bloquant pour la
  démonstration du système
- Un seul véhicule fixe par tournée (pas de gestion de flotte multi-véhicules)
