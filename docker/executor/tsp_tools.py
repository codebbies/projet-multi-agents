"""Outils de reoptimisation d'itineraire (TSP bas-carbone), fournis comme module
pret a l'emploi dans la sandbox de l'agent Executeur -- pour eviter de demander
au LLM de reimplementer un algorithme d'optimisation a chaque appel.

Modelise la tournee comme un CHEMIN OUVERT (pas un circuit ferme) : le vehicule
part du depot et visite chaque arret une fois, sans obligation de retour au
depot dans les donnees (coherent avec la structure reelle de fact_route_leg).
"""
import math
from typing import List, Sequence, Tuple

Coord = Tuple[float, float]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _distance_matrix(coords: Sequence[Coord]) -> List[List[float]]:
    n = len(coords)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine_km(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def path_distance_km(order: Sequence[int], coords: Sequence[Coord]) -> float:
    total = 0.0
    for i in range(len(order) - 1):
        a, b = coords[order[i]], coords[order[i + 1]]
        total += haversine_km(a[0], a[1], b[0], b[1])
    return total


def _nearest_neighbor_path(dist: List[List[float]], start_idx: int) -> List[int]:
    n = len(dist)
    visited = [False] * n
    order = [start_idx]
    visited[start_idx] = True
    current = start_idx
    for _ in range(n - 1):
        nearest, nearest_d = None, float("inf")
        for j in range(n):
            if not visited[j] and dist[current][j] < nearest_d:
                nearest, nearest_d = j, dist[current][j]
        order.append(nearest)
        visited[nearest] = True
        current = nearest
    return order


def _two_opt_path(order: List[int], dist: List[List[float]], max_passes: int = 30) -> List[int]:
    n = len(order)
    improved = True
    passes = 0
    while improved and passes < max_passes:
        improved = False
        passes += 1
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                a, b = order[i - 1], order[i]
                c, d = order[j], order[j + 1]
                before = dist[a][b] + dist[c][d]
                after = dist[a][c] + dist[b][d]
                if after + 1e-9 < before:
                    order[i:j + 1] = reversed(order[i:j + 1])
                    improved = True
    return order


def solve_tsp_path(coords: Sequence[Coord], start_idx: int = 0) -> Tuple[List[int], float]:
    """Retourne (ordre optimise des indices, distance totale en km) pour un
    chemin ouvert commencant a start_idx et visitant tous les points de coords."""
    dist = _distance_matrix(coords)
    order = _nearest_neighbor_path(dist, start_idx)
    order = _two_opt_path(order, dist)
    return order, path_distance_km(order, coords)
