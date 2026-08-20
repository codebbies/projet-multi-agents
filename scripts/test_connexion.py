"""US 1.1 - critère d'acceptation : valide la connexion à Azure OpenAI avec un prompt basique."""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

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

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)

response = client.chat.completions.create(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    messages=[{"role": "user", "content": "Réponds uniquement par : Connexion Azure OpenAI OK"}],
    max_tokens=20,
)

print(response.choices[0].message.content)
