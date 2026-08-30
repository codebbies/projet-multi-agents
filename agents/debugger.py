"""US 3.2 - Debugging automatique.

Different du flux Executeur habituel (US 2.2) : ici, le script n'est PAS ecrit
par l'agent depuis un plan - il est fourni par l'utilisateur, deja buggue.
Le systeme l'execute tel quel, capture la trace d'erreur, puis boucle
diagnostic (Critique) -> correction (Correcteur) -> re-execution, jusqu'a
succes ou limite de tours.
"""
import re
from dataclasses import dataclass, field
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock, CodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

CRITIC_DEBUG_SYSTEM_MESSAGE = """Tu es le Critique, specialise dans le diagnostic \
d'erreurs Python.

Tu recois un script qui a plante et sa trace d'erreur complete (traceback).
Ton role : identifier la cause RACINE de l'erreur, pas juste repeter le message \
d'exception. Sois precis et actionnable.

Exemple de bon diagnostic : "KeyError: 'emission_co2e' - la colonne s'appelle \
emission_kg_co2e dans fact_route_leg.csv, le nom utilise dans le script est \
incorrect (probablement une confusion avec une autre colonne similaire)."

Ne propose pas de code corrige toi-meme - ce n'est pas ton role, tu diagnostiques \
uniquement.
"""

FIXER_SYSTEM_MESSAGE = """Tu es un correcteur de code Python.

Tu recois : le script original qui a plante, sa trace d'erreur, et le diagnostic \
du Critique. Ta tache : renvoyer la version CORRIGEE COMPLETE du script, dans un \
seul bloc ```python.

Regles :
1. Ne corrige QUE ce qui cause l'erreur diagnostiquee - ne reecris pas le script \
depuis zero, ne change pas la logique qui fonctionnait deja.
2. Le bloc de code doit etre complet et autonome (tous les imports, toutes les \
variables necessaires) - il sera execute seul, sans memoire du tour precedent.
3. Ne mets aucun texte hors du bloc ```python - seulement le code.
"""


def get_critic_debug_agent(model_client: AzureOpenAIChatCompletionClient) -> AssistantAgent:
    return AssistantAgent(
        name="CritiqueDebug",
        model_client=model_client,
        system_message=CRITIC_DEBUG_SYSTEM_MESSAGE,
    )


def get_fixer_agent(model_client: AzureOpenAIChatCompletionClient) -> AssistantAgent:
    return AssistantAgent(
        name="Correcteur",
        model_client=model_client,
        system_message=FIXER_SYSTEM_MESSAGE,
    )


@dataclass
class DebugResult:
    success: bool
    final_code: str
    tours: int
    history: list = field(default_factory=list)


def _extract_code_block(text: str) -> str:
    match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


async def debug_script(
    code_executor: CodeExecutor,
    buggy_code: str,
    model_client: AzureOpenAIChatCompletionClient,
    max_tours: int = 5,
) -> DebugResult:
    """Execute buggy_code tel quel, puis boucle diagnostic->correction jusqu'a
    succes ou max_tours atteint. Correspond exactement aux 3 criteres
    d'acceptation US 3.2."""
    critic = get_critic_debug_agent(model_client)
    fixer = get_fixer_agent(model_client)
    token = CancellationToken()
    current_code = buggy_code
    history: list[dict[str, Any]] = []

    for tour in range(1, max_tours + 1):
        result = await code_executor.execute_code_blocks(
            [CodeBlock(language="python", code=current_code)],
            cancellation_token=token,
        )
        history.append(
            {
                "tour": tour,
                "code": current_code,
                "output": result.output,
                "exit_code": result.exit_code,
            }
        )

        if result.exit_code == 0:
            return DebugResult(success=True, final_code=current_code, tours=tour, history=history)

        diag_result = await critic.run(
            task=(
                f"Script qui a plante :\n```python\n{current_code}\n```\n\n"
                f"Trace d'erreur :\n{result.output}\n\n"
                f"Diagnostique la cause racine."
            )
        )
        diagnosis = diag_result.messages[-1].to_text()

        fix_result = await fixer.run(
            task=(
                f"Script original :\n```python\n{current_code}\n```\n\n"
                f"Trace d'erreur :\n{result.output}\n\n"
                f"Diagnostic du Critique :\n{diagnosis}\n\n"
                f"Renvoie la version corrigee complete du script."
            )
        )
        current_code = _extract_code_block(fix_result.messages[-1].to_text())

    return DebugResult(success=False, final_code=current_code, tours=max_tours, history=history)
