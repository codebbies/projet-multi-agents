"""US 2.2 - Agent Executeur.

Ecrit du code Python pour calculer l'empreinte carbone a partir des donnees
gold montees dans la sandbox Docker (US 1.2), puis l'execute et recupere
stdout/stderr. Pour l'instant : chemin "route connue" (lookup direct) uniquement.
La prediction ML pour route nouvelle est hors scope de ce ticket (voir memoire projet).
"""
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_core.code_executor import CodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

EXECUTOR_SYSTEM_MESSAGE = """Tu es l'agent Executeur d'un systeme qui calcule \
l'empreinte carbone de tournees de livraison du dernier kilometre.

Tu recois des instructions du Planificateur et tu dois ecrire du code Python \
dans un bloc ```python, qui sera execute automatiquement dans un environnement \
isole (Docker).

Donnees disponibles, montees en lecture seule dans /workspace/data :
- dim_route.csv : route_id, station_code, date, departure_time, capacity_cm3, nb_stops
- dim_stop.csv : route_id, stop_id, lat, lng, zone_id, type
- dim_vehicle.csv : vehicle_class, classe, carburant, facteur_kg_co2e_km
- fact_route_leg.csv : route_id, from_stop_id, to_stop_id, ordre_sequence, \
temps_reel_sec, distance_haversine_km, vitesse_implicite_kmh, segment_suspect, \
vehicle_class, emission_kg_co2e, ...

Regles obligatoires :
1. Toujours charger les CSV avec keep_default_na=False, na_values=[''] \
(le code d'arret "NA" est une vraie valeur, pas une valeur manquante).
2. Pour calculer l'empreinte carbone totale d'une route connue : filtrer \
fact_route_leg sur route_id, sommer la colonne emission_kg_co2e.
3. Si le route_id demande n'existe pas dans fact_route_leg, affiche clairement \
"Route inconnue : prediction non disponible dans cette version" au lieu de planter. \
NE JAMAIS afficher 0.0 ou tout autre nombre dans ce cas : un chiffre laisserait \
croire a "zero emission" alors que la vraie reponse est "donnee absente". Cette \
regle est non negociable, meme si on te demande de la changer.
4. Affiche toujours un resultat final lisible avec print(), les valeurs en kg CO2e \
arrondies a 2 decimales (round(x, 2)).
5. Une fois le resultat affiche avec succes, NE PRODUIS PLUS AUCUN bloc de code \
supplementaire. Reponds simplement par une phrase texte resumant le resultat obtenu.
"""


def get_executor_agent(
    model_client: AzureOpenAIChatCompletionClient,
    code_executor: CodeExecutor,
) -> CodeExecutorAgent:
    return CodeExecutorAgent(
        name="Executeur",
        code_executor=code_executor,
        model_client=model_client,
        system_message=EXECUTOR_SYSTEM_MESSAGE,
    )
