"""US 1.2 - critère d'acceptation : l'agent Exécuteur exécute du code via AutoGen
dans la sandbox Docker, lit data/gold, et ne peut pas y écrire."""
import asyncio

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock

from executor_sandbox import get_executor


async def main() -> None:
    executor = get_executor()
    await executor.start()
    try:
        token = CancellationToken()
        read_result = await executor.execute_code_blocks(
            [
                CodeBlock(
                    language="python",
                    code=(
                        "import pandas as pd\n"
                        "df = pd.read_csv('/workspace/data/dim_stop.csv', "
                        "keep_default_na=False, na_values=[''])\n"
                        "print(f'Lignes lues : {len(df)}')\n"
                    ),
                )
            ],
            cancellation_token=token,
        )
        print("--- Lecture des données gold ---")
        print(read_result.output)
        assert read_result.exit_code == 0, "La lecture des données gold a échoué"

        write_result = await executor.execute_code_blocks(
            [
                CodeBlock(
                    language="python",
                    code="open('/workspace/data/test.txt', 'w').write('dangereux')\n",
                )
            ],
            cancellation_token=token,
        )
        print("--- Tentative d'écriture sur les données gold (doit échouer) ---")
        print(write_result.output)
        assert write_result.exit_code != 0, "L'écriture sur data/gold aurait dû être refusée !"

        print("\nOK : lecture des données gold fonctionne, écriture bien refusée.")
    finally:
        await executor.stop()


if __name__ == "__main__":
    asyncio.run(main())
