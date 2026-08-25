"""US 2.3 - Boucle de collaboration Executeur <-> Critique.

L'Executeur ecrit/execute du code, le Critique verifie et donne un feedback.
Le cycle s'arrete automatiquement quand le Critique repond APPROUVE, ou apres
un nombre maximal de tours (garde-fou anti-boucle-infinie, cf. Bug 1 du cahier
des charges).
"""
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.code_executor import CodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

from agents.critic import get_critic_agent
from agents.executor import get_executor_agent

MAX_TOURS = 6


def get_executor_critic_team(
    model_client: AzureOpenAIChatCompletionClient,
    code_executor: CodeExecutor,
) -> RoundRobinGroupChat:
    executor_agent = get_executor_agent(model_client, code_executor)
    critic_agent = get_critic_agent(model_client)

    termination = TextMentionTermination("APPROUVE") | MaxMessageTermination(MAX_TOURS)

    return RoundRobinGroupChat(
        [executor_agent, critic_agent],
        termination_condition=termination,
    )
