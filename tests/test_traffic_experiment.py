import json

import networkx as nx
import numpy as np

from algorithms.aco import ACOConfig
from algorithms.route_optimizer import RouteOptimizer
from network.distance_matrix import compute_route_cost_matrix
from optimization.cost_function import ObjectiveWeights
from traffic.traffic_simulator import TrafficSimulator


def _experiment_graph(depot, stops):
    points = [depot, *stops]
    graph = nx.MultiDiGraph()
    for node, (latitude, longitude) in enumerate(points):
        graph.add_node(node, x=longitude, y=latitude, lat=latitude, lon=longitude)
    for source in range(len(points)):
        for target in range(len(points)):
            if source == target:
                continue
            length_m = 1000.0 + ((source * 13 + target * 7) % 7) * 20.0
            speed_kph = 20.0 + ((source * 5 + target * 3) % 11)
            graph.add_edge(
                source,
                target,
                key=0,
                length_m=length_m,
                speed_kph=speed_kph,
                travel_time_minutes=length_m / 1000.0 / speed_kph * 60.0,
            )
    return graph


def test_controlled_normal_vs_heavy_traffic_experiment():
    depot = (10.0, 10.0)
    stops = [(10.01, 10.0), (10.02, 10.0), (10.03, 10.0), (10.04, 10.0), (10.05, 10.0)]
    graph = _experiment_graph(depot, stops)
    config = ACOConfig(
        num_ants=40,
        iterations=60,
        alpha=1.0,
        beta=3.0,
        evaporation_rate=0.2,
        random_seed=11,
    )
    weights = ObjectiveWeights(distance=0.5, time=0.3, fuel=0.2)
    optimizer = RouteOptimizer(graph, depot, stops, config=config)

    normal_matrices = compute_route_cost_matrix(graph, depot, stops)
    normal = optimizer.optimize(weights=weights)
    all_edges = list(graph.edges(keys=True))
    simulator = TrafficSimulator(seed=42)
    simulator.apply_congestion(graph, all_edges, level="heavy")
    simulator.update_all_travel_times(graph)
    heavy_matrices = compute_route_cost_matrix(graph, depot, stops)
    heavy = optimizer.optimize(
        weights=weights,
        normalization_baseline=normal.normalization_baseline,
    )

    assert np.array_equal(normal_matrices["distance_km"], heavy_matrices["distance_km"])
    assert np.array_equal(normal_matrices["fuel_liters"], heavy_matrices["fuel_liters"])
    assert not np.array_equal(
        normal_matrices["travel_time_minutes"],
        heavy_matrices["travel_time_minutes"],
    )
    assert heavy.metrics["travel_time_minutes"] > normal.metrics["travel_time_minutes"]
    assert heavy.metrics["combined_cost"] > normal.metrics["combined_cost"]
    assert all(
        np.isfinite(value)
        for value in (
            normal.metrics["distance_km"],
            normal.metrics["travel_time_minutes"],
            normal.metrics["fuel_liters"],
            normal.metrics["combined_cost"],
            heavy.metrics["distance_km"],
            heavy.metrics["travel_time_minutes"],
            heavy.metrics["fuel_liters"],
            heavy.metrics["combined_cost"],
        )
    )

    print(json.dumps({
        "fixed_inputs": {
            "depot": depot,
            "stops": stops,
            "vehicle_km_per_litre": 12.0,
            "aco": {
                "num_ants": config.num_ants,
                "iterations": config.iterations,
                "alpha": config.alpha,
                "beta": config.beta,
                "evaporation_rate": config.evaporation_rate,
                "random_seed": config.random_seed,
            },
            "weights": weights.as_tuple(),
            "normalization_baseline": normal.normalization_baseline,
        },
        "normal": {
            "route": normal.route,
            "distance_km": normal.metrics["distance_km"],
            "travel_time_minutes": normal.metrics["travel_time_minutes"],
            "fuel_liters": normal.metrics["fuel_liters"],
            "combined_cost": normal.metrics["combined_cost"],
        },
        "heavy": {
            "route": heavy.route,
            "distance_km": heavy.metrics["distance_km"],
            "travel_time_minutes": heavy.metrics["travel_time_minutes"],
            "fuel_liters": heavy.metrics["fuel_liters"],
            "combined_cost": heavy.metrics["combined_cost"],
        },
        "matrix_comparison": {
            "same_distance_matrix": bool(np.array_equal(
                normal_matrices["distance_km"], heavy_matrices["distance_km"]
            )),
            "same_fuel_matrix": bool(np.array_equal(
                normal_matrices["fuel_liters"], heavy_matrices["fuel_liters"]
            )),
            "travel_time_matrix_changed": not np.array_equal(
                normal_matrices["travel_time_minutes"], heavy_matrices["travel_time_minutes"]
            ),
        },
    }, sort_keys=True))
