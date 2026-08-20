"""Audit du star schema data/gold : structure, clés, intégrité référentielle."""
import pandas as pd

GOLD = "data/gold"


def load(name):
    return pd.read_csv(f"{GOLD}/{name}.csv", keep_default_na=False, na_values=[""])


def main():
    dim_route = load("dim_route")
    dim_stop = load("dim_stop")
    dim_vehicle = load("dim_vehicle")
    fact = load("fact_route_leg")

    tables = {
        "dim_route": dim_route,
        "dim_stop": dim_stop,
        "dim_vehicle": dim_vehicle,
        "fact_route_leg": fact,
    }

    print("=" * 60)
    print("1. STRUCTURE DES TABLES")
    print("=" * 60)
    for name, df in tables.items():
        print(f"\n--- {name} ---")
        print(f"Lignes : {len(df)}")
        print(f"Colonnes : {list(df.columns)}")

    print("\n" + "=" * 60)
    print("2. CLES DES DIMENSIONS (unicite)")
    print("=" * 60)

    n_total, n_unique = len(dim_route), dim_route["route_id"].nunique()
    print(f"dim_route.route_id (cle simple) : {n_unique}/{n_total} -> {'OK' if n_total == n_unique else 'DOUBLONS !'}")

    n_total = len(dim_stop)
    n_unique_simple = dim_stop["stop_id"].nunique()
    n_unique_composite = dim_stop.drop_duplicates(subset=["route_id", "stop_id"]).shape[0]
    print(f"dim_stop.stop_id seul : {n_unique_simple}/{n_total} valeurs uniques (normal, stop_id se repete entre routes)")
    print(f"dim_stop (route_id, stop_id) cle composite : {n_unique_composite}/{n_total} -> {'OK' if n_total == n_unique_composite else 'DOUBLONS !'}")

    n_total, n_unique = len(dim_vehicle), dim_vehicle["vehicle_class"].nunique()
    print(f"dim_vehicle.vehicle_class (cle) : {n_unique}/{n_total} -> {'OK' if n_total == n_unique else 'DOUBLONS !'}")

    print("\n" + "=" * 60)
    print("3. INTEGRITE REFERENTIELLE (foreign keys de fact_route_leg)")
    print("=" * 60)
    print(f"Colonnes de fact_route_leg : {list(fact.columns)}")

    orphans_route = ~fact["route_id"].isin(dim_route["route_id"])
    print(f"fact.route_id -> dim_route.route_id : {orphans_route.sum()} orphelins")

    dim_stop_keys = set(zip(dim_stop["route_id"], dim_stop["stop_id"]))
    from_keys = set(zip(fact["route_id"], fact["from_stop_id"]))
    to_keys = set(zip(fact["route_id"], fact["to_stop_id"]))
    orphans_from = from_keys - dim_stop_keys
    orphans_to = to_keys - dim_stop_keys
    print(f"fact.(route_id, from_stop_id) -> dim_stop.(route_id, stop_id) : {len(orphans_from)} combinaisons orphelines")
    print(f"fact.(route_id, to_stop_id) -> dim_stop.(route_id, stop_id) : {len(orphans_to)} combinaisons orphelines")

    orphans_vehicle = ~fact["vehicle_class"].isin(dim_vehicle["vehicle_class"])
    print(f"fact.vehicle_class -> dim_vehicle.vehicle_class : {orphans_vehicle.sum()} orphelins")

    print("\n" + "=" * 60)
    print("4. VALEURS MANQUANTES")
    print("=" * 60)
    for name, df in tables.items():
        nulls = df.isna().sum()
        nulls = nulls[nulls > 0]
        if len(nulls) > 0:
            print(f"\n{name} :")
            print(nulls)
        else:
            print(f"{name} : aucune valeur manquante")

    print("\n" + "=" * 60)
    print("5. GRAIN DE LA TABLE DE FAITS")
    print("=" * 60)
    print(f"Lignes fact_route_leg : {len(fact)}")
    id_cols = [c for c in fact.columns if c.endswith("_id")]
    if id_cols:
        n_dup = len(fact) - len(fact.drop_duplicates(subset=id_cols))
        print(f"Doublons sur {id_cols} : {n_dup}")


if __name__ == "__main__":
    main()
