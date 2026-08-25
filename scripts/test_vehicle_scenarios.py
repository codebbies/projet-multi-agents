"""Complexification US 2.2/2.3 : comparaison de scenarios vehicule (donnee reelle
vs essence/hybride/electrique pour LA MEME tournee). Test du pipeline complet
Planificateur -> Executeur -> Critique sur une requete en langage naturel."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.executor_critic_team import get_executor_critic_team
from agents.model_client import get_model_client
from agents.planner import get_planner_agent
from executor_sandbox import get_executor

ROUTE_CONNUE = "RouteID_01c30168-2365-46a5-a1c0-60cfafe18c6f"


async def main() -> None:
    model_client = get_model_client()
    code_executor = get_executor()
    await code_executor.start()

    try:
        # 1. Le Planificateur decompose la demande utilisateur
        planner = get_planner_agent(model_client)
        requete = (
            f"Le van diesel de la route {ROUTE_CONNUE} aurait-il pu emettre moins "
            f"avec un autre type de vehicule ?"
        )
        plan_result = await planner.run(task=requete)
        plan = plan_result.messages[-1].to_text()

        print("=" * 60)
        print("PLAN DU PLANIFICATEUR")
        print("=" * 60)
        print(plan)

        # 2. L'equipe Executeur-Critique execute le plan
        team = get_executor_critic_team(model_client, code_executor)
        team_task = (
            f"Voici le plan a suivre :\n{plan}\n\n"
            f"Route concernee : {ROUTE_CONNUE}. "
            f"Compare l'empreinte carbone reelle aux 3 scenarios de vehicule "
            f"alternatif (essence, hybride rechargeable, electrique) pour cette "
            f"tournee, et indique le scenario le plus favorable avec le % de gain."
        )
        result = await team.run(task=team_task)

        print("\n" + "=" * 60)
        print("ECHANGE EXECUTEUR <-> CRITIQUE")
        print("=" * 60)
        for msg in result.messages:
            print(f"[{msg.source}] {msg.to_text()[:600]}")
            print()

        approuve = any("APPROUVE" in m.to_text() for m in result.messages)
        assert approuve, "Le Critique n'a jamais valide le resultat final"
        print("OK : pipeline complet Planificateur -> Executeur -> Critique valide.")
    finally:
        await code_executor.stop()
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
