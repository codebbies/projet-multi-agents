"""Complexification 3 : prediction ML pour route nouvelle (arrets pas encore
connus, seulement caracteristiques de planification). Pipeline complet
Planificateur -> Executeur (modele carbon_predictor.pkl) -> Critique."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.executor_critic_team import get_executor_critic_team
from agents.model_client import get_model_client
from agents.planner import get_planner_agent
from executor_sandbox import get_executor


async def main() -> None:
    model_client = get_model_client()
    code_executor = get_executor()
    await code_executor.start()

    try:
        planner = get_planner_agent(model_client)
        requete = (
            "On planifie une nouvelle tournee, pas encore dans l'historique : "
            "zone DLA7, environ 150 arrets, capacite 4247923 cm3, van diesel. "
            "Quelle empreinte carbone peut-on estimer avant de connaitre le "
            "detail exact des arrets ?"
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
            f"Caracteristiques de la nouvelle tournee (pas d'arrets connus) : "
            f"station_code=DLA7, nb_stops=150, capacity_cm3=4247923, "
            f"vehicle_class=van_class3_diesel. Utilise le modele de prediction "
            f"pour estimer l'empreinte carbone totale."
        )
        result = await team.run(task=team_task)

        print("\n" + "=" * 60)
        print("ECHANGE EXECUTEUR <-> CRITIQUE")
        print("=" * 60)
        for msg in result.messages:
            print(f"[{msg.source}] {msg.to_text()[:700]}")
            print()

        approuve = any("APPROUVE" in m.to_text() for m in result.messages)
        assert approuve, "Le Critique n'a jamais valide le resultat final"
        print("OK : prediction ML validee par le pipeline complet.")
    finally:
        await code_executor.stop()
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
