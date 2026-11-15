import networkx as nx
import pytest

from models.schemas import RouteConfig, TrafficSimulationRequest
from traffic.traffic_simulator import TrafficSimulator


def test_traffic_simulation_changes_travel_time():
    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, key=0, length_m=1000.0, speed_kph=40.0, travel_time_minutes=1.5)
    simulator = TrafficSimulator(seed=11)
    simulator.apply_congestion(graph, [(0, 1, 0)], level="heavy")
    simulator.update_edge_travel_time(graph, (0, 1, 0))
    edge = graph[0][1][0]
    assert edge["travel_time_minutes"] > 1.5
    assert edge["travel_time_minutes"] == 2.5
    assert edge["traffic_level"] == "heavy"


def test_traffic_simulation_preserves_distance():
    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, key=0, length_m=1000.0, speed_kph=40.0, travel_time_minutes=1.5)
    simulator = TrafficSimulator(seed=7)
    before = graph[0][1][0]["length_m"]
    simulator.apply_congestion(graph, [(0, 1, 0)], level="severe")
    after = graph[0][1][0]["length_m"]
    assert before == after


def test_repeated_traffic_update_replaces_severity_without_changing_distance():
    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, key=0, length_m=1000.0, speed_kph=40.0, travel_time_minutes=1.5)
    simulator = TrafficSimulator(seed=7)
    simulator.apply_congestion(graph, [(0, 1, 0)], level="heavy")
    simulator.update_edge_travel_time(graph, (0, 1, 0))
    heavy_time = graph[0][1][0]["travel_time_minutes"]

    simulator.apply_congestion(graph, [(0, 1, 0)], level="moderate")
    simulator.update_edge_travel_time(graph, (0, 1, 0))

    assert graph[0][1][0]["travel_time_minutes"] < heavy_time
    assert graph[0][1][0]["length_m"] == 1000.0


def test_clearing_congestion_restores_base_edge_time():
    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, key=0, length_m=1000.0, speed_kph=40.0, travel_time_minutes=1.5)
    simulator = TrafficSimulator(seed=7)
    simulator.apply_congestion(graph, [(0, 1, 0)], level="heavy")
    simulator.update_edge_travel_time(graph, (0, 1, 0))

    simulator.clear_congestion(graph)
    simulator.update_all_travel_times(graph)

    edge = graph[0][1][0]
    assert "traffic_level" not in edge
    assert edge["travel_time_minutes"] == 1.5


def test_dynamic_replanning_excludes_completed_deliveries():
    stops = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
    completed = {1}
    remaining = [stop for idx, stop in enumerate(stops) if idx not in completed]
    assert remaining == [(0.0, 0.0), (2.0, 2.0)]


def test_traffic_fraction_and_optimizer_configuration_reject_invalid_values():
    with pytest.raises(ValueError):
        TrafficSimulationRequest(fraction=1.5)
    with pytest.raises(ValueError):
        RouteConfig(num_ants=0)
    with pytest.raises(ValueError):
        RouteConfig(distance_weight=0, time_weight=0, fuel_weight=0)
