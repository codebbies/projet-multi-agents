"""US 3.2 - criteres d'acceptation :
1. Le systeme execute le script buggue et capture la stack trace.
2. Le Critic analyse l'erreur et l'Executor (Correcteur) propose un correctif.
3. Le script corrige s'execute avec succes et produit le resultat attendu.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.debugger import debug_script
from agents.model_client import get_model_client
from executor_sandbox import get_executor

# Script volontairement buggue : mauvais nom de colonne (emission_co2e au lieu
# de emission_kg_co2e), exactement le type d'erreur que le Critique anticipe
# deja dans agents/critic.py.
SCRIPT_BUGGUE = """import pandas as pd

fact = pd.read_csv('/workspace/data/fact_route_leg.csv', keep_default_na=False, na_values=[''])
route = fact[fact['route_id'] == 'RouteID_01c30168-2365-46a5-a1c0-60cfafe18c6f']
total = route['emission_co2e'].sum()
print(f"Empreinte carbone totale : {round(total, 2)} kg CO2e")
"""


async def main() -> None:
    model_client = get_model_client()
    code_executor = get_executor()
    await code_executor.start()

    try:
        print("--- Script buggue soumis ---")
        print(SCRIPT_BUGGUE)

        result = await debug_script(code_executor, SCRIPT_BUGGUE, model_client, max_tours=5)

        print(f"\n--- Historique ({len(result.history)} tour(s)) ---")
        for entry in result.history:
            print(f"\nTour {entry['tour']} (exit_code={entry['exit_code']}) :")
            print(entry["output"][:400])

        print("\n--- Script final ---")
        print(result.final_code)

        assert result.success, f"Le debugging a echoue apres {result.tours} tours"
        assert "21.18" in result.history[-1]["output"], "Le resultat final devrait afficher 21.18 kg CO2e"
        print(f"\nOK : script corrige en {result.tours} tour(s), resultat correct.")
    finally:
        await code_executor.stop()
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
