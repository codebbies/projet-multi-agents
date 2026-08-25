"""US 1.2 - Câblage AutoGen <-> sandbox Docker de l'agent Exécuteur.

Fournit un DockerCommandLineCodeExecutor prêt à l'emploi, basé sur l'image
`lastmile-executor:latest` (voir docker/executor/Dockerfile), avec le dossier
data/gold monté en lecture seule.
"""
from pathlib import Path

from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = PROJECT_ROOT / "data" / "gold"
MODELS_DIR = PROJECT_ROOT / "models"
WORK_DIR = PROJECT_ROOT / "scripts" / ".executor_work"


def get_executor() -> DockerCommandLineCodeExecutor:
    """Instancie l'executor Docker de l'agent Exécuteur.

    - image lastmile-executor:latest : Python + pandas/numpy, utilisateur non-root
    - data/gold monté en lecture seule : l'agent peut lire les données mais jamais les modifier
    - models/ monté en lecture seule : modele de prediction pre-entraine (train_carbon_predictor.py)
    """
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    return DockerCommandLineCodeExecutor(
        image="lastmile-executor:latest",
        work_dir=WORK_DIR,
        timeout=60,
        extra_volumes={
            str(GOLD_DIR): {"bind": "/workspace/data", "mode": "ro"},
            str(MODELS_DIR): {"bind": "/workspace/models", "mode": "ro"},
        },
    )
