"""Entrainement local (pas Azure ML) d'un modele Random Forest baseline qui
predit l'empreinte carbone TOTALE d'une tournee a partir de ses caracteristiques
de planification (zone, nb d'arrets, capacite, vehicule) -- utile pour estimer
une tournee AVANT de connaitre le detail exact des arrets.

Note importante : dans ce dataset, emission_kg_co2e = distance_haversine_km x
facteur_kg_co2e_km EXACTEMENT (verifie, ecart ~1e-15). Donc si les arrets sont
deja connus, le calcul est deterministe (pas besoin de ML, cf. agents/executor.py
regle 2). Ce modele sert uniquement au cas "route pas encore detaillee".
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD = PROJECT_ROOT / "data" / "gold"
MODELS_DIR = PROJECT_ROOT / "models"


def build_training_table() -> pd.DataFrame:
    dim_route = pd.read_csv(GOLD / "dim_route.csv", keep_default_na=False, na_values=[""])
    fact = pd.read_csv(GOLD / "fact_route_leg.csv", keep_default_na=False, na_values=[""])

    per_route = fact.groupby("route_id").agg(
        emission_totale_kg_co2e=("emission_kg_co2e", "sum"),
        vehicle_class=("vehicle_class", "first"),
    ).reset_index()

    table = dim_route.merge(per_route, on="route_id", how="inner")
    return table


def main() -> None:
    table = build_training_table()

    categorical_cols = ["station_code", "vehicle_class"]
    numeric_cols = ["nb_stops", "capacity_cm3"]
    target_col = "emission_totale_kg_co2e"

    X = pd.get_dummies(table[categorical_cols + numeric_cols], columns=categorical_cols)
    y = table[target_col]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    print(f"Nombre de routes d'entrainement : {len(X_train)}")
    print(f"Nombre de routes de test : {len(X_test)}")
    print(f"R2 (test) : {r2:.3f}")
    print(f"MAE (test) : {mae:.2f} kg CO2e")
    print(f"Emission moyenne (reference) : {y.mean():.2f} kg CO2e")

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODELS_DIR / "carbon_predictor.pkl")

    with open(MODELS_DIR / "carbon_predictor_columns.json", "w", encoding="utf-8") as f:
        json.dump(list(X.columns), f, indent=2)

    with open(MODELS_DIR / "carbon_predictor_metrics.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "r2_test": round(r2, 3),
                "mae_test_kg_co2e": round(mae, 2),
                "emission_moyenne_kg_co2e": round(y.mean(), 2),
                "n_train": len(X_train),
                "n_test": len(X_test),
            },
            f,
            indent=2,
        )

    print(f"\nModele sauvegarde dans {MODELS_DIR}/")


if __name__ == "__main__":
    main()
