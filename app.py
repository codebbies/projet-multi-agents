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

EXEMPLES = {
    "Substitution vehicule": (
        "Le van diesel de la route RouteID_01c30168-2365-46a5-a1c0-60cfafe18c6f "
        "aurait-il pu emettre moins avec un autre type de vehicule ?"
    ),
    "TSP bas-carbone": (
        "Le livreur de la route RouteID_01c30168-2365-46a5-a1c0-60cfafe18c6f "
        "a-t-il suivi l'ordre d'arrets le plus efficace ?"
    ),
    "Prediction ML (route nouvelle)": (
        "On planifie une nouvelle tournee, pas encore dans l'historique : "
        "zone DLA7, environ 150 arrets, capacite 4247923 cm3, van diesel. "
        "Quelle empreinte carbone peut-on estimer ?"
    ),
}


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
                if source == "Executeur":
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

    with st.sidebar:
        st.markdown("### 🌱 Pipeline Carbone Last-Mile")
        st.caption("Planificateur → Executeur → Critique")

        st.markdown("**Sandbox Docker**")
        st.success("🔒 Toujours active — lecture seule + reseau coupe (non desactivable)")

        st.markdown("**Exemples de requetes**")
        for label, texte in EXEMPLES.items():
            if st.button(label, use_container_width=True):
                st.session_state.requete_actuelle = texte

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
        c1.metric("Tokens utilises", f"{total_tokens:,}".replace(",", " "))
        c2.metric("Cout estime", f"${cout_estime:.4f}")
        c3.metric("Messages echanges", len(resultat["messages"]))
        st.caption(
            "Cout estime a titre indicatif (tarifs publics gpt-4.1-mini), "
            "les tarifs Azure reels dependent du contrat."
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
