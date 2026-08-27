# Déroulé de démo — Sprint 2

## Avant de commencer

```bash
docker info
```
Si erreur -> ouvrir Docker Desktop, attendre l'icône stable, réessayer.

Se placer dans le bon dossier :
```bash
cd "C:\Users\ASUS\Documents\projet_multi_agents\scripts"
```

## 1. Contexte (1 min, à l'oral, pas de commande)

Montrer l'artifact "Pipeline Carbone Last-Mile" (schéma d'architecture).
Points clés à dire :
- 3 agents (Planificateur, Exécuteur, Critique), architecture imposée par le cahier des charges
- Données réelles : 1000 routes Amazon Last-Mile
- Exécution isolée en sandbox Docker (sécurité : le code généré par le LLM ne peut jamais toucher aux vraies données)

## 2. Levier 1 — Substitution véhicule (le plus fiable, à faire en premier)

```bash
python test_vehicle_scenarios.py
```

**Ce qu'il faut dire pendant que ça tourne (10-20s d'attente)** :
"Le Planificateur décompose la question en langage naturel, l'Exécuteur écrit
et exécute du code Python dans le conteneur Docker, le Critique vérifie avant
de valider."

**Résultat attendu** : ~21.18 kg CO2e réel vs ~11.45 kg avec un hybride rechargeable,
gain ~46%.

## 3. Levier 2 — TSP bas-carbone

```bash
python test_tsp.py
```

**Ce qu'il faut dire** : "Ici l'Exécuteur n'invente pas d'algorithme lui-même —
il appelle un module que j'ai écrit et testé séparément (nearest-neighbor + 2-opt),
plus fiable que de faire réinventer un algo d'optimisation par le LLM à chaque fois."

**Résultat attendu** : gain modeste ~6%, cohérent (un livreur réel suit déjà
un itinéraire raisonnable).

## 4. Levier 3 — Prédiction ML (route nouvelle)

```bash
python test_ml_prediction.py
```

**Ce qu'il faut dire** : "Pour une tournée qui n'existe pas encore dans
l'historique, un modèle Random Forest entraîné en local estime l'empreinte.
R² de 0.51 — un baseline honnête, pas un modèle miracle, assumé comme tel
par le système lui-même."

## 5. Sécurité de la sandbox — écriture bloquée

```bash
cd ..
docker run --rm -v "${PWD}\data\gold:/workspace/data:ro" lastmile-executor:latest python3 -c "open('/workspace/data/test.txt','w').write('x')"
```
Doit afficher `Read-only file system`. Preuve visuelle forte et rapide.

## 6. Sécurité de la sandbox — réseau coupé

```bash
docker run --rm --network none -v "${PWD}\data\gold:/workspace/data:ro" lastmile-executor:latest python3 -c "import urllib.request; urllib.request.urlopen('http://example.com', timeout=5)"
```
Doit afficher `Temporary failure in name resolution`.

**Ce qu'il faut dire** : "Le code généré par le LLM ne peut ni modifier les
données, ni faire sortir la moindre donnée vers l'extérieur — deux couches
d'isolation testées et prouvées, pas juste affirmées."

---

## SI UN SCRIPT ÉCHOUE EN LIVE

Ne pas paniquer, ne pas cacher. Dire :

> "Le Critique n'a pas validé du premier coup — c'est normal, c'est le
> garde-fou anti-boucle-infinie prévu par le cahier des charges (Bug 1).
> Je relance."

Puis relancer la même commande une fois. Si ça échoue une seconde fois,
montrer le fichier backup correspondant :

```bash
cat ../demo_backup/1_scenarios_vehicule.txt
# ou 2_tsp_bas_carbone.txt / 3_prediction_ml.txt
```

En disant : "Voici une exécution réussie capturée plus tôt — le système n'est
pas déterministe (c'est un LLM), mais le mécanisme est bien réel, pas simulé."

C'est plus crédible d'assumer la non-déterminisme que de prétendre que tout
marche à 100% à chaque fois.
