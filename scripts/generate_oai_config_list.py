"""Génère OAI_CONFIG_LIST (format AutoGen) à partir des variables d'environnement du .env."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

required = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
]
missing = [name for name in required if not os.getenv(name)]
if missing:
    raise SystemExit(f"Variables manquantes dans .env : {', '.join(missing)}")

config_list = [
    {
        "model": os.environ["AZURE_OPENAI_DEPLOYMENT"],
        "api_key": os.environ["AZURE_OPENAI_API_KEY"],
        "base_url": os.environ["AZURE_OPENAI_ENDPOINT"],
        "api_type": "azure",
        "api_version": os.environ["AZURE_OPENAI_API_VERSION"],
    }
]

output_path = PROJECT_ROOT / "OAI_CONFIG_LIST"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(config_list, f, indent=2)

print(f"{output_path} généré.")
