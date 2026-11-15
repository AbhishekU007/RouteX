from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import networkx as nx
import numpy as np

from network.road_network import snap_to_nearest_node, validate_coordinates
from optimization.fuel_estimator import estimate_fuel_consumption


def _compute_path_metrics(graph: nx.MultiDiGraph, source: int, target: int) -> tuple[float, float, List[int]]:
    if source == target:
        return 0.0, 0.0, [source]

    try:
        path = nx.shortest_path(graph, source, target, weight="length_m")
    except nx.NetworkXNoPath:
        return math.inf, math.inf, []

    total_distance_m = 0.0
    total_time_minutes = 0.0
    for u, v in zip(path, path[1:]):
        edge_data = graph.get_edge_data(u, v)
        if not edge_data:
            return math.inf, math.inf, []
        selected = min(
            edge_data.values(),
            key=lambda data: (
                float(data.get("length_m", data.get("length", 0.0))),
                float(data.get("travel_time_minutes", math.inf)),
            ),
        )
        length_m = float(selected.get("length_m", selected.get("length", 0.0)))
        if not math.isfinite(length_m) or length_m < 0:
            return math.inf, math.inf, []
        total_distance_m += length_m
        if "travel_time_minutes" in selected and math.isfinite(float(selected["travel_time_minutes"])):
            total_time_minutes += max(0.0, float(selected["travel_time_minutes"]))
        else:
            speed_kph = float(selected.get("speed_kph", 35.0) or 35.0)
            total_time_minutes += max(0.0, length_m / 1000.0 / max(speed_kph, 1.0) * 60.0)

    distance_km = total_distance_m / 1000.0
    time_minutes = max(0.0, total_time_minutes)
    return distance_km, time_minutes, path


def compute_route_cost_matrix(
    graph: nx.MultiDiGraph,
    depot: Tuple[float, float],
    stops: Sequence[Tuple[float, float]],
    mileage_km_per_litre: float = 12.0,
    traffic_factor: float = 1.0,
    congestion_multiplier: float = 1.0,
) -> dict:
    if not stops:
        raise ValueError("At least one stop is required to compute route matrices.")

    all_points = [depot] + list(stops)
    snapped = []
    for latitude, longitude in all_points:
        validate_coordinates(latitude, longitude)
        snapped.append(snap_to_nearest_node(graph, latitude, longitude))

    n = len(snapped)
    distance_matrix = np.full((n, n), np.inf, dtype=float)
    time_matrix = np.full((n, n), np.inf, dtype=float)
    fuel_matrix = np.full((n, n), np.inf, dtype=float)
    paths: dict[tuple[int, int], List[int]] = {}

    for i, source in enumerate(snapped):
        for j, target in enumerate(snapped):
            if i == j:
                distance_matrix[i, j] = 0.0
                time_matrix[i, j] = 0.0
                fuel_matrix[i, j] = 0.0
                paths[(i, j)] = [source]
                continue
            distance_km, time_minutes, path = _compute_path_metrics(graph, source, target)
            if not path:
                continue
            if not math.isfinite(distance_km) or not math.isfinite(time_minutes):
                continue
            distance_matrix[i, j] = distance_km
            time_matrix[i, j] = time_minutes
            fuel_matrix[i, j] = estimate_fuel_consumption(
                distance_km,
                mileage_km_per_litre=mileage_km_per_litre,
                traffic_factor=traffic_factor,
                congestion_multiplier=congestion_multiplier,
            )
            paths[(i, j)] = path

    return {
        "distance_km": distance_matrix,
        "travel_time_minutes": time_matrix,
        "fuel_liters": fuel_matrix,
        "paths": paths,
        "nodes": snapped,
    }


def shortest_path_between(graph: nx.MultiDiGraph, source: int, target: int) -> tuple[float, float, List[int]]:
    return _compute_path_metrics(graph, source, target)
