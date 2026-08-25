"""US 2.1 - critere d'acceptation : le Planificateur genere un plan numerote,
en langage naturel, sans jamais produire de code."""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.model_client import get_model_client
from agents.planner import get_planner_agent

REQUETE_TEST = (
    "Quelle est l'empreinte carbone de la route R_1 ? "
    "Si elle n'existe pas dans l'historique, propose une estimation."
)


async def main() -> None:
    model_client = get_model_client()
    planner = get_planner_agent(model_client)

    result = await planner.run(task=REQUETE_TEST)
    plan_text = result.messages[-1].content

    print("--- Plan genere par le Planificateur ---")
    print(plan_text)
    print()

    numbered_steps = re.findall(r"^\s*\d+\.", plan_text, flags=re.MULTILINE)
    assert len(numbered_steps) >= 2, "Le plan doit contenir plusieurs etapes numerotees"

    assert "```" not in plan_text, "Le Planificateur ne doit jamais produire de bloc de code"

    print(f"OK : {len(numbered_steps)} etapes numerotees, aucun bloc de code detecte.")
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
