"""US 2.2 - criteres d'acceptation : l'Executeur genere un script Python valide,
l'execute dans Docker, et on recupere stdout/stderr."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.executor import get_executor_agent
from agents.model_client import get_model_client
from executor_sandbox import get_executor

ROUTE_CONNUE = "RouteID_01c30168-2365-46a5-a1c0-60cfafe18c6f"


async def main() -> None:
    model_client = get_model_client()
    code_executor = get_executor()
    await code_executor.start()

    executor_agent = get_executor_agent(model_client, code_executor)

    try:
        task = (
            f"Ecris et execute le code Python qui calcule la somme de la colonne "
            f"emission_kg_co2e pour la route {ROUTE_CONNUE} dans fact_route_leg.csv, "
            f"puis affiche le resultat avec print()."
        )
        result = await executor_agent.run(task=task)

        print("--- Echange complet ---")
        for msg in result.messages:
            print(f"[{msg.source}] {msg.to_text()[:500]}")
            print()

        last_output = result.messages[-1].to_text()
        assert "kg" in last_output.lower() or "co2" in last_output.lower(), (
            "Le resultat final devrait contenir un chiffre d'emission"
        )
        print("OK : code genere, execute dans Docker, resultat recupere.")
    finally:
        await code_executor.stop()
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
