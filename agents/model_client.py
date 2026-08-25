"""Client Azure OpenAI partage entre les agents (Planificateur, Executeur, Critique)."""
import os
from pathlib import Path

from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_model_client() -> AzureOpenAIChatCompletionClient:
    return AzureOpenAIChatCompletionClient(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        model="gpt-4.1-mini-2025-04-14",
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": False,
        },
    )
