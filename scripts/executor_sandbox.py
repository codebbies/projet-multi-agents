"""US 1.2 - Câblage AutoGen <-> sandbox Docker de l'agent Exécuteur.

Fournit un DockerCommandLineCodeExecutor prêt à l'emploi, basé sur l'image
`lastmile-executor:latest` (voir docker/executor/Dockerfile), avec le dossier
data/gold monté en lecture seule, et le réseau coupé (aucun accès internet
depuis le code execute par le LLM - voir _disable_network).
"""
import logging
from pathlib import Path

import docker
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = PROJECT_ROOT / "data" / "gold"
MODELS_DIR = PROJECT_ROOT / "models"
WORK_DIR = PROJECT_ROOT / "scripts" / ".executor_work"


def _disable_network(executor: DockerCommandLineCodeExecutor) -> None:
    """Deconnecte le conteneur de tout reseau Docker une fois demarre.

    DockerCommandLineCodeExecutor n'expose pas de parametre network_mode,
    donc on coupe le reseau apres coup via le SDK docker : le code genere
    par le LLM ne peut alors faire aucune requete sortante (exfiltration
    de donnees, appel a une API externe non prevue, etc.).
    """
    client = docker.from_env()
    container = client.containers.get(executor.container_name)
    networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    for network_name in list(networks.keys()):
        client.networks.get(network_name).disconnect(container, force=True)
    logging.debug(f"Reseau coupe pour le conteneur {executor.container_name}")


def get_executor() -> DockerCommandLineCodeExecutor:
    """Instancie l'executor Docker de l'agent Exécuteur.

    - image lastmile-executor:latest : Python + pandas/numpy, utilisateur non-root
    - data/gold monté en lecture seule : l'agent peut lire les données mais jamais les modifier
    - models/ monté en lecture seule : modele de prediction pre-entraine (train_carbon_predictor.py)
    - reseau coupe une fois le conteneur demarre (voir _disable_network)
    """
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    executor = DockerCommandLineCodeExecutor(
        image="lastmile-executor:latest",
        work_dir=WORK_DIR,
        timeout=60,
        extra_volumes={
            str(GOLD_DIR): {"bind": "/workspace/data", "mode": "ro"},
            str(MODELS_DIR): {"bind": "/workspace/models", "mode": "ro"},
        },
    )

    original_start = executor.start

    async def start_and_isolate() -> None:
        await original_start()
        _disable_network(executor)

    executor.start = start_and_isolate
    return executor
