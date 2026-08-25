"""Complexification 2 : TSP bas-carbone. Pipeline complet Planificateur ->
Executeur (utilise tsp_tools.solve_tsp_path) -> Critique sur une requete en
langage naturel demandant si l'ordre des arrets aurait pu etre meilleur."""
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
        planner = get_planner_agent(model_client)
        requete = (
            f"Le livreur de la route {ROUTE_CONNUE} a-t-il suivi l'ordre "
            f"d'arrets le plus efficace, ou aurait-il pu reduire ses emissions "
            f"en visitant les arrets dans un autre ordre ?"
        )
        plan_result = await planner.run(task=requete)
        plan = plan_result.messages[-1].to_text()

        print("=" * 60)
        print("PLAN DU PLANIFICATEUR")
        print("=" * 60)
        print(plan)

        team = get_executor_critic_team(model_client, code_executor)
        team_task = (
            f"Voici le plan a suivre :\n{plan}\n\n"
            f"Route concernee : {ROUTE_CONNUE}. Utilise tsp_tools.solve_tsp_path "
            f"pour trouver un ordre d'arrets optimise, compare sa distance et son "
            f"empreinte carbone estimee a la tournee reelle, et indique le gain "
            f"potentiel en % et en kg CO2e evitables."
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
        print("OK : TSP bas-carbone valide par le pipeline complet.")
    finally:
        await code_executor.stop()
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
