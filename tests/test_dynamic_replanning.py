import json

import networkx as nx
import numpy as np
import pytest

from algorithms.aco import AntColonyOptimizer
from algorithms.route_optimizer import RouteOptimizer, _build_objective_matrix
from models.schemas import OptimizationRequest, ReplanRequest, RouteConfig
from network.distance_matrix import compute_route_cost_matrix
from optimization.cost_function import ObjectiveWeights
from services import optimizer_service
from traffic.traffic_simulator import TrafficSimulator


def _complete_test_network(depot, stops):
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


def test_replan_uses_current_position_remaining_stops_and_updated_traffic(monkeypatch):
    depot = (10.0, 10.0)
    stops = [(10.01, 10.0), (10.02, 10.0), (10.03, 10.0), (10.04, 10.0), (10.05, 10.0)]
    graph = _complete_test_network(depot, stops)
    simulator = TrafficSimulator(seed=42)
    monkeypatch.setitem(optimizer_service.STATE, "city", "test city")
    monkeypatch.setitem(optimizer_service.STATE, "network", graph)
    monkeypatch.setitem(optimizer_service.STATE, "depot", depot)
    monkeypatch.setitem(optimizer_service.STATE, "stops", stops)
    monkeypatch.setitem(optimizer_service.STATE, "route_result", None)
    monkeypatch.setitem(optimizer_service.STATE, "original_route_result", None)
    monkeypatch.setitem(optimizer_service.STATE, "latest_replanned_route", None)
    monkeypatch.setitem(optimizer_service.STATE, "route_history", [])
    monkeypatch.setitem(optimizer_service.STATE, "traffic_comparison", {
        "normal_traffic_baseline": None,
        "simulated_congestion_scenario": None,
    })
    monkeypatch.setitem(optimizer_service.STATE, "traffic_simulator", simulator)
    monkeypatch.setitem(
        optimizer_service.STATE,
        "traffic_status",
        {"source": "simulated", "available": False, "status": "normal"},
    )

    config = RouteConfig(num_ants=40, iterations=60, random_seed=11)
    initial = optimizer_service.optimize_route(
        OptimizationRequest(city="test city", depot=depot, stops=stops, config=config)
    )
    initial_stops = [entry["index"] for entry in initial["sequence"] if entry["type"] == "stop"]
    completed = initial_stops[:2]
    next_remaining = next(index for index in initial_stops if index not in completed)
    remaining_ids = [index for index in range(len(stops)) if index not in completed]
    current_position = stops[completed[-1]]
    current_node = completed[-1] + 1
    target_node = next_remaining + 1

    before_matrices = compute_route_cost_matrix(
        graph,
        current_position,
        [*[stops[index] for index in remaining_ids], depot],
    )
    before_objective, _ = _build_objective_matrix(before_matrices, ObjectiveWeights())

    simulator.apply_congestion(graph, [(current_node, target_node, 0)], level="heavy")
    simulator.update_all_travel_times(graph)
    assert graph[current_node][target_node][0]["length_m"] == 1000.0 + (
        (current_node * 13 + target_node * 7) % 7
    ) * 20.0
    after_matrices = compute_route_cost_matrix(
        graph,
        current_position,
        [*[stops[index] for index in remaining_ids], depot],
    )
    after_objective, _ = _build_objective_matrix(after_matrices, ObjectiveWeights())
    target_matrix_index = remaining_ids.index(next_remaining) + 1

    optimizer_inputs = []
    original_optimize = AntColonyOptimizer.optimize

    def capture_optimizer_input(self, cost_matrix, end_node=None):
        optimizer_inputs.append((np.asarray(cost_matrix).copy(), end_node))
        return original_optimize(self, cost_matrix, end_node=end_node)

    monkeypatch.setattr(AntColonyOptimizer, "optimize", capture_optimizer_input)
    monkeypatch.setitem(
        optimizer_service.STATE,
        "traffic_status",
        {"source": "simulated", "available": False, "status": "heavy", "city": "test city"},
    )
    replanned = optimizer_service.replan_remaining(
        ReplanRequest(completed=completed, config=config)
    )

    assert len(optimizer_inputs) == 1
    assert np.allclose(optimizer_inputs[0][0], after_objective)
    assert after_matrices["travel_time_minutes"][0, target_matrix_index] > before_matrices["travel_time_minutes"][0, target_matrix_index]
    assert after_objective[0, target_matrix_index] > before_objective[0, target_matrix_index]
    assert replanned["current_position"] == {
        "latitude": current_position[0],
        "longitude": current_position[1],
    }

    visited = replanned["route_stop_indices"]
    assert len(visited) == len(set(visited))
    assert set(visited).isdisjoint(completed)
    assert sorted(visited) == remaining_ids
    assert replanned["sequence"][0]["type"] == "current"
    assert replanned["sequence"][-1]["type"] == "depot"
    assert replanned["original_route"]["route"] == initial["route"]
    assert replanned["previous_metrics"] == initial["metrics"]
    analytics = optimizer_service.get_analytics()
    assert analytics["original_complete_route"]["route"] == initial["route"]
    assert analytics["active_route"]["route"] == replanned["route"]
    assert analytics["replanned_route"]["route"] == replanned["route"]
    assert analytics["normal_traffic_baseline"]["route"] == initial["route"]
    assert analytics["simulated_congestion_scenario"]["traffic_status"]["status"] == "heavy"
    assert analytics["simulated_congestion_scenario"]["route"]["route"] == replanned["route"]

    route = replanned["route"]
    expected_time = sum(
        after_matrices["travel_time_minutes"][left, right]
        for left, right in zip(route, route[1:])
    )
    assert np.isclose(replanned["metrics"]["travel_time_minutes"], expected_time)
    assert np.isfinite(replanned["metrics"]["distance_km"])
    assert np.isfinite(replanned["metrics"]["travel_time_minutes"])
    assert np.isfinite(replanned["metrics"]["fuel_liters"])
    print(json.dumps({
        "initial_route": initial["route"],
        "completed_stop_indices": completed,
        "current_position": replanned["current_position"],
        "remaining_stop_indices": replanned["route_stop_indices"],
        "previous_metrics": replanned["previous_metrics"],
        "updated_metrics": replanned["metrics"],
        "traffic_cost_before": float(before_objective[0, target_matrix_index]),
        "traffic_cost_after": float(after_objective[0, target_matrix_index]),
    }, sort_keys=True))

    with pytest.raises(ValueError, match="valid stop indices"):
        optimizer_service.replan_remaining(ReplanRequest(completed=[len(stops)], config=config))


def test_replan_with_all_deliveries_completed_returns_to_depot_with_real_metrics():
    depot = (10.0, 10.0)
    stops = [(10.01, 10.0), (10.02, 10.0)]
    graph = _complete_test_network(depot, stops)

    result = RouteOptimizer(graph, depot, stops).replan_remaining(
        completed=[0, 1],
        current_position=stops[1],
    )

    assert result.route == [0, 1]
    assert result.stop_order == []
    assert result.metrics["distance_km"] > 0
    assert result.metrics["travel_time_minutes"] > 0


def test_optimization_rejects_city_that_does_not_match_loaded_network(monkeypatch):
    depot = (10.0, 10.0)
    stops = [(10.01, 10.0)]
    graph = _complete_test_network(depot, stops)
    monkeypatch.setitem(optimizer_service.STATE, "city", "Agra, Uttar Pradesh, India")
    monkeypatch.setitem(optimizer_service.STATE, "network", graph)

    with pytest.raises(ValueError, match="Load the road network"):
        optimizer_service.optimize_route(
            OptimizationRequest(city="Delhi, India", depot=depot, stops=stops)
        )

    assert optimizer_service.STATE["city"] == "Agra, Uttar Pradesh, India"


def test_route_geometry_includes_osm_edge_shape_points():
    from types import SimpleNamespace

    graph = nx.MultiDiGraph()
    graph.add_node(0, x=10.0, y=20.0)
    graph.add_node(1, x=10.02, y=20.0)
    graph.add_edge(
        0,
        1,
        key=0,
        length_m=2000.0,
        geometry=SimpleNamespace(coords=[(10.0, 20.0), (10.01, 20.01), (10.02, 20.0)]),
    )

    geometry = optimizer_service._route_geometry(graph, [0, 1])

    assert geometry == [[20.0, 10.0], [20.01, 10.01], [20.0, 10.02]]
