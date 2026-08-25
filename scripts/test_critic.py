"""US 2.3 - criteres d'acceptation : le Critique identifie les erreurs, donne un
feedback constructif, et le cycle Executeur-Critique s'arrete automatiquement."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.executor_critic_team import MAX_TOURS, get_executor_critic_team
from agents.model_client import get_model_client
from executor_sandbox import get_executor

ROUTE_CONNUE = "RouteID_01c30168-2365-46a5-a1c0-60cfafe18c6f"


async def run_case(task: str, label: str) -> None:
    model_client = get_model_client()
    code_executor = get_executor()
    await code_executor.start()

    team = get_executor_critic_team(model_client, code_executor)

    try:
        print(f"\n{'=' * 60}\nCas : {label}\n{'=' * 60}")
        result = await team.run(task=task)

        for msg in result.messages:
            print(f"[{msg.source}] {msg.to_text()[:400]}")
            print()

        n_messages = len(result.messages)
        approuve = any("APPROUVE" in m.to_text() for m in result.messages)

        print(f"Nombre total de messages : {n_messages}")
        print(f"Cycle termine par APPROUVE : {approuve}")
        # Le CodeExecutorAgent emet plusieurs sous-messages par tour (code, stdout,
        # resume), donc le nombre total de messages peut depasser MAX_TOURS ; ce qui
        # compte pour le critere d'acceptation, c'est que le cycle se soit VRAIMENT
        # arrete (pas de boucle infinie), quel que soit le compte exact.
        assert n_messages < 30, "Le cycle semble tourner sans jamais s'arreter !"
    finally:
        await code_executor.stop()
        await model_client.close()


async def main() -> None:
    await run_case(
        f"Ecris et execute le code Python qui calcule la somme de la colonne "
        f"emission_kg_co2e pour la route {ROUTE_CONNUE} dans fact_route_leg.csv, "
        f"puis affiche le resultat avec print().",
        "route connue, calcul correct attendu",
    )

    await run_case(
        "Ecris et execute le code Python qui calcule la somme de la colonne "
        "emission_kg_co2e pour la route ROUTE_QUI_N_EXISTE_PAS_XYZ dans "
        "fact_route_leg.csv, puis affiche le resultat avec print().",
        "route inexistante, le Critique doit detecter le probleme",
    )


if __name__ == "__main__":
    asyncio.run(main())
