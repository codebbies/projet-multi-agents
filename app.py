"""Interface Streamlit du Pipeline Carbone Last-Mile.

Palette et choix de design decides avant construction (voir memoire projet) :
- vert (coherent avec le schema d'architecture deja publie), pas le violet
  d'une reference vue en cours de route
- pas de gamification (confettis) - outil ESG serieux, pas un assistant
  de code ludique
- le resultat cle (kg CO2e) doit etre visible immediatement, pas enterre
  dans un modal
- la sandbox Docker n'est jamais desactivable (contrairement a une reference
  vue qui proposait un toggle) - coherent avec le travail de securite fait
- suivi tokens/cout en direct - repond a une question laissee sans reponse
  dans le Q&A de demo
- badge du levier utilise (lookup exact / TSP exact / prediction ML) - la
  fiabilite du chiffre differe selon le chemin
"""
import asyncio
import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.executor_critic_team import MAX_TOURS, get_executor_critic_team
from agents.model_client import get_model_client
from agents.planner import get_planner_agent
from scripts.executor_sandbox import get_executor

# Tarification indicative gpt-4.1-mini (Azure OpenAI), a titre d'estimation
# uniquement - les tarifs reels dependent du contrat Azure et peuvent varier.
PRIX_INPUT_PAR_1M = 0.40
PRIX_OUTPUT_PAR_1M = 1.60

# 5 routes reelles verifiees dans data/gold, choisies pour couvrir la variete
# reelle du dataset (38 a 222 arrets, 4 zones differentes) - eviter de ne
# montrer qu'UNE SEULE route dans toute la demo, ce qui ferait croire a tort
# que le systeme est cable en dur sur un cas unique.
ROUTES_REFERENCE = {
    "Route courte - 38 arrets (zone DBO1)": "RouteID_04189f85-13a6-47b8-a78e-ec5688be0819",
    "Route moyenne - 130 arrets (zone DLA7)": "RouteID_11ff0b06-87ec-4755-a731-2a2c3dfd45a4",
    "Route moyenne - 151 arrets (zone DLA7)": "RouteID_0df605eb-a6e2-4f8a-ac76-b4f8b74ac68e",
    "Route longue - 170 arrets (zone DCH4)": "RouteID_1364e982-c768-4248-818f-cefad0f4b136",
    "Route tres longue - 222 arrets (zone DBO3)": "RouteID_06c23b69-370a-4a37-a941-8a3e177b1914",
}

# Toutes les vraies routes du dataset utilisent le meme vehicule reel
# (van_class3_diesel) - verifie sur les 1000 routes. Les autres vehicules
# n'existent que comme scenarios hypothetiques (colonnes emission_scenario_*).


def requete_substitution_vehicule(route_id: str) -> str:
    return f"Le van diesel de la route {route_id} aurait-il pu emettre moins avec un autre type de vehicule ?"


def requete_tsp(route_id: str) -> str:
    return f"Le livreur de la route {route_id} a-t-il suivi l'ordre d'arrets le plus efficace ?"


def requete_lookup(route_id: str) -> str:
    return f"Quelle est l'empreinte carbone de la route {route_id} ?"


REQUETE_ML_TYPE = (
    "On planifie une nouvelle tournee, pas encore dans l'historique : "
    "zone DLA7, environ 150 arrets, capacite 4247923 cm3, van diesel. "
    "Quelle empreinte carbone peut-on estimer ?"
)


def detecter_levier(messages: list[dict]) -> tuple[str, str]:
    """Heuristique simple sur TOUTE la conversation (pas seulement le dernier
    message, qui peut etre une confirmation courte du Critique sans mots-cles)
    pour indiquer quel levier de calcul a probablement ete utilise.
    Best-effort, pas garanti."""
    t = " ".join(m["content"] for m in messages).lower()
    # Ordre important : criteres les plus specifiques d'abord, "estimation"
    # seul est trop generique (utilise aussi dans d'autres leviers).
    if "tsp" in t or "ordre optimis" in t or "reordonn" in t:
        return "TSP bas-carbone (calcul exact)", "green"
    if "hybride" in t or "electrique" in t or ("scenario" in t and "essence" in t):
        return "Substitution vehicule (calcul exact)", "green"
    if "random forest" in t or "carbon_predictor" in t or "r2=" in t or "r²=" in t:
        return "Prediction ML (estimation)", "orange"
    if "route inconnue" in t:
        return "Route inconnue", "red"
    return "Calcul direct (lookup, exact)", "green"


def nettoyer_reponse(texte: str) -> str:
    """Retire les artefacts techniques internes qui ne doivent jamais
    s'afficher a l'utilisateur final (ex: mot-cle de terminaison)."""
    return re.sub(r"\bTERMINATE\b", "", texte).strip()


async def executer_pipeline(requete: str, conteneur_status) -> dict:
    model_client = get_model_client()
    code_executor = get_executor()
    await code_executor.start()

    total_prompt_tokens = 0
    total_completion_tokens = 0
    messages_log: list[dict] = []
    approuve = False
    dernier_texte = ""
    dernier_texte_executeur = ""

    try:
        conteneur_status.update(label="Le Planificateur decompose la demande...")
        planner = get_planner_agent(model_client)
        plan_result = await planner.run(task=requete)
        plan = plan_result.messages[-1].to_text()
        for m in plan_result.messages:
            if m.models_usage:
                total_prompt_tokens += m.models_usage.prompt_tokens
                total_completion_tokens += m.models_usage.completion_tokens

        conteneur_status.update(label="L'Executeur et le Critique travaillent...")
        team = get_executor_critic_team(model_client, code_executor)
        team_task = f"Voici le plan a suivre :\n{plan}\n\nRequete originale : {requete}"

        async for event in team.run_stream(task=team_task):
            source = getattr(event, "source", None)
            content = getattr(event, "content", None)
            usage = getattr(event, "models_usage", None)
            if usage:
                total_prompt_tokens += usage.prompt_tokens
                total_completion_tokens += usage.completion_tokens
            if source and content and isinstance(content, str) and source != "user":
                messages_log.append({"source": source, "content": content})
                dernier_texte = content
                # Ne retenir que les messages "prose" de l'Executeur comme
                # resultat principal - un bloc de code brut n'est pas un
                # resultat lisible, meme si c'est techniquement son dernier
                # message (arrive quand le Critique approuve juste apres
                # le code, avant que l'Executeur resume en langage naturel).
                if source == "Executeur" and not content.strip().startswith("```"):
                    dernier_texte_executeur = content
                if "APPROUVE" in content:
                    approuve = True
                conteneur_status.update(label=f"{source} vient de repondre...")

        conteneur_status.update(label="Termine", state="complete")
    finally:
        await code_executor.stop()
        await model_client.close()

    return {
        "plan": plan,
        "messages": messages_log,
        "approuve": approuve,
        "reponse_finale": nettoyer_reponse(dernier_texte_executeur or dernier_texte),
        "avis_critique": nettoyer_reponse(dernier_texte) if approuve else "",
        "tokens_prompt": total_prompt_tokens,
        "tokens_completion": total_completion_tokens,
    }


def main() -> None:
    st.set_page_config(
        page_title="Pipeline Carbone Last-Mile",
        page_icon="🌱",
        layout="wide",
    )

    if "historique" not in st.session_state:
        st.session_state.historique = []
    if "requete_actuelle" not in st.session_state:
        st.session_state.requete_actuelle = ""
    if "route_choisie" not in st.session_state:
        st.session_state.route_choisie = list(ROUTES_REFERENCE.keys())[0]

    with st.sidebar:
        st.markdown("### 🌱 Pipeline Carbone Last-Mile")
        st.caption("Planificateur → Executeur → Critique")

        st.markdown("**Sandbox Docker**")
        st.success("🔒 Toujours active — lecture seule + reseau coupe (non desactivable)")

        st.markdown("**Route de reference**")
        st.session_state.route_choisie = st.selectbox(
            "Choisir une route reelle du dataset",
            options=list(ROUTES_REFERENCE.keys()),
            index=list(ROUTES_REFERENCE.keys()).index(st.session_state.route_choisie),
            label_visibility="collapsed",
        )
        route_id = ROUTES_REFERENCE[st.session_state.route_choisie]
        st.caption(f"`{route_id}`")

        st.markdown("**Leviers de calcul (sur la route choisie)**")
        if st.button("Substitution vehicule", use_container_width=True):
            st.session_state.requete_actuelle = requete_substitution_vehicule(route_id)
        if st.button("TSP bas-carbone", use_container_width=True):
            st.session_state.requete_actuelle = requete_tsp(route_id)
        if st.button("Calcul direct (lookup)", use_container_width=True):
            st.session_state.requete_actuelle = requete_lookup(route_id)
        if st.button("Prediction ML (route nouvelle)", use_container_width=True):
            st.session_state.requete_actuelle = REQUETE_ML_TYPE

        if st.button("↺ Reinitialiser", use_container_width=True):
            st.session_state.requete_actuelle = ""
            st.rerun()

        with st.expander("Methodologie et valeur ajoutee"):
            st.markdown(
                "**Sources de donnees.** Amazon Last-Mile Routing Research "
                "Challenge (routes, sequences d'arrets, temps de trajet "
                "reels - 1000 tournees, 5 metropoles US, 2018) croise avec "
                "les facteurs d'emission DEFRA (UK Department for "
                "Environment), reference standard pour le reporting GHG "
                "Protocol Scope 1-3.\n\n"
                "**Deux niveaux de valeur.**\n\n"
                "- Declaratif : mesure precise de l'empreinte par tournee, "
                "utile pour le reporting reglementaire (CSRD, Scope 3) "
                "independamment de toute action operationnelle.\n"
                "- Operationnel : le TSP optimise une marge mecaniquement "
                "limitee (vehicule fixe, facteur d'emission constant sur la "
                "tournee ; gain de 6 a 15% observe selon la route). La "
                "substitution de vehicule (jusqu'a -46%) suppose un "
                "renouvellement de flotte, decision a horizon de plusieurs "
                "annees.\n\n"
                "**Justification du systeme multi-agents.** Pour un calcul "
                "fixe, un script suffirait. L'interet est de traiter des "
                "requetes en langage naturel non specifiees a l'avance, "
                "avec une verification independante (agent Critique) avant "
                "restitution du resultat."
            )

        if st.session_state.historique:
            st.markdown("**Historique de la session**")
            for i, entry in enumerate(reversed(st.session_state.historique)):
                with st.expander(entry["requete"][:50] + "..."):
                    st.write(entry["reponse_finale"])
                    st.caption(f"{entry['tokens_prompt'] + entry['tokens_completion']} tokens")

    st.title("Empreinte carbone d'une tournee last-mile")
    st.caption(
        "Systeme multi-agents (AutoGen + Azure OpenAI) sur donnees reelles "
        "Amazon Last-Mile. Le code genere par le LLM s'execute dans une "
        "sandbox Docker isolee."
    )
    st.markdown(
        "**Objectif** : mesurer l'empreinte carbone de chaque tournée à "
        "partir de données de routes réelles (Amazon Last-Mile Routing "
        "Research Challenge) et des facteurs d'émission DEFRA (référence "
        "pour le reporting GHG Protocol Scope 1-3, CSRD), et permettre "
        "l'interrogation du système en langage naturel plutôt que par une "
        "interface figée. Méthodologie détaillée dans la sidebar."
    )

    requete = st.text_area(
        "Votre demande",
        value=st.session_state.requete_actuelle,
        height=100,
        placeholder="Ex: quelle est l'empreinte carbone de la route X ?",
    )

    if st.button("Lancer les agents", type="primary"):
        if not requete.strip():
            st.warning("Ecris une demande avant de lancer les agents.")
            return

        with st.status("Demarrage de la sandbox Docker...", expanded=True) as status:
            try:
                resultat = asyncio.run(executer_pipeline(requete, status))
            except Exception as e:
                status.update(label="Erreur", state="error")
                st.error(
                    f"Erreur : {e}\n\n"
                    "Verifie que Docker Desktop est bien lance."
                )
                return

        levier, couleur = detecter_levier(resultat["messages"])

        st.markdown("### Resultat")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(resultat["reponse_finale"])
        with col2:
            if couleur == "green":
                st.success(f"📊 {levier}")
            elif couleur == "orange":
                st.warning(f"📊 {levier}")
            else:
                st.error(f"📊 {levier}")

        if resultat["approuve"]:
            st.caption(f"✓ Approuve par le Critique — {resultat['avis_critique'][:200]}")
        else:
            st.caption(
                f"⚠ Le Critique n'a pas explicitement approuve dans la limite "
                f"de {MAX_TOURS} tours (garde-fou anti-boucle-infinie)."
            )

        total_tokens = resultat["tokens_prompt"] + resultat["tokens_completion"]
        cout_estime = (
            resultat["tokens_prompt"] / 1_000_000 * PRIX_INPUT_PAR_1M
            + resultat["tokens_completion"] / 1_000_000 * PRIX_OUTPUT_PAR_1M
        )
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Tokens utilises",
            f"{total_tokens:,}".replace(",", " "),
            help=f"{resultat['tokens_prompt']:,} en entree + {resultat['tokens_completion']:,} en sortie".replace(",", " "),
        )
        c2.metric("Cout estime", f"${cout_estime:.4f}")
        c3.metric("Messages echanges", len(resultat["messages"]))
        st.caption(
            "Cout estime a titre indicatif : tarifs publics gpt-4.1-mini "
            f"(entree ${PRIX_INPUT_PAR_1M}/1M, sortie ${PRIX_OUTPUT_PAR_1M}/1M tokens - "
            "la sortie coute plus cher que l'entree, d'ou des couts qui ne sont "
            "pas strictement proportionnels au nombre total de tokens). "
            "Les tarifs Azure reels dependent du contrat."
        )

        with st.expander("Plan du Planificateur"):
            st.text(resultat["plan"])

        with st.expander("Echange complet Executeur ↔ Critique"):
            for m in resultat["messages"]:
                st.markdown(f"**{m['source']}**")
                st.text(m["content"][:1000])
                st.divider()

        st.session_state.historique.append({"requete": requete, **resultat})


if __name__ == "__main__":
    main()
