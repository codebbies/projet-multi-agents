"""Sprint 1 - Hello World multi-agents : conversation simple entre deux agents AutoGen,
connectes a Azure OpenAI, pour valider que l'installation AutoGen fonctionne de bout en bout."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console

from agents.model_client import get_model_client


async def main() -> None:
    model_client = get_model_client()

    agent_a = AssistantAgent(
        name="Alice",
        model_client=model_client,
        system_message="Tu es Alice. Reponds en une phrase courte, salue et pose une question simple.",
    )
    agent_b = AssistantAgent(
        name="Bob",
        model_client=model_client,
        system_message="Tu es Bob. Reponds en une phrase courte a Alice.",
    )

    team = RoundRobinGroupChat(
        [agent_a, agent_b],
        termination_condition=MaxMessageTermination(4),
    )

    await Console(team.run_stream(task="Dis bonjour a Bob."))
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
