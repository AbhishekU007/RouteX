import networkx as nx
import numpy as np
import pytest

from network.distance_matrix import compute_route_cost_matrix, shortest_path_between
from network.road_network import load_road_network, validate_coordinates
from models.schemas import OptimizationRequest


def test_validate_coordinates_accepts_valid_input():
    validate_coordinates(28.6139, 77.2090)


def test_invalid_coordinates_are_rejected():
    try:
        validate_coordinates(91.0, 0.0)
        raise AssertionError("Expected a ValueError for invalid latitude.")
    except ValueError:
        pass


def test_empty_graph_rejected_for_snap():
    graph = nx.MultiDiGraph()
    with pytest.raises(ValueError, match="empty"):
        from network.road_network import snap_to_nearest_node

        snap_to_nearest_node(graph, 0.0, 0.0)


def test_unreachable_location_pair_is_infinite_in_distance_matrix():
    graph = nx.MultiDiGraph()
    graph.add_node(0, x=0.0, y=0.0)
    graph.add_node(1, x=1.0, y=1.0)
    graph.add_node(2, x=2.0, y=2.0)
    graph.add_edge(0, 1, key=0, length_m=1000.0, speed_kph=30.0)

    matrices = compute_route_cost_matrix(graph, (0.0, 0.0), [(2.0, 2.0)])

    assert np.isinf(matrices["distance_km"][0, 1])
    assert np.isinf(matrices["travel_time_minutes"][0, 1])


def test_parallel_edges_use_shortest_distance_edge_and_its_travel_time():
    graph = nx.MultiDiGraph()
    graph.add_node(0, x=0.0, y=0.0)
    graph.add_node(1, x=1.0, y=1.0)
    graph.add_edge(0, 1, key=0, length_m=1000.0, travel_time_minutes=5.0, speed_kph=20.0)
    graph.add_edge(0, 1, key=1, length_m=1000.0, travel_time_minutes=2.0, speed_kph=40.0)

    distance, duration, path = shortest_path_between(graph, 0, 1)

    assert path == [0, 1]
    assert distance == 1.0
    assert duration == 2.0


def test_directed_one_way_edge_is_not_reversed_by_network_cost_matrix():
    graph = nx.MultiDiGraph()
    graph.add_node(0, x=0.0, y=0.0)
    graph.add_node(1, x=1.0, y=1.0)
    graph.add_edge(0, 1, key=0, length_m=1000.0, speed_kph=30.0, travel_time_minutes=2.0)

    matrices = compute_route_cost_matrix(graph, (0.0, 0.0), [(1.0, 1.0)])

    assert np.isfinite(matrices["distance_km"][0, 1])
    assert np.isinf(matrices["distance_km"][1, 0])


def test_optimization_request_rejects_out_of_range_coordinates():
    with pytest.raises(ValueError):
        OptimizationRequest(depot=(91.0, 0.0), stops=[(0.0, 0.0)])
    with pytest.raises(ValueError):
        OptimizationRequest(depot=(0.0, 0.0), stops=[(0.0, 181.0)])


def test_osmnx_edge_length_is_preserved_in_meters(monkeypatch):
    import network.road_network as road_network

    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, length=1500.0)
    monkeypatch.setattr(road_network, "_has_osm_access", lambda: True)
    monkeypatch.setattr(road_network.ox, "geocode", lambda city, timeout: (0.0, 0.0))
    monkeypatch.setattr(road_network.ox, "graph_from_place", lambda city, network_type, simplify, timeout: graph)

    loaded = load_road_network("test city", offline_only=False)

    assert loaded[0][1][0]["length_m"] == 1500.0
    assert loaded[0][1][0]["length_m"] != 1_500_000.0
    assert loaded.graph["source"] == "openstreetmap"


def test_offline_network_identifies_its_source_and_reason():
    graph = load_road_network("Agra, Uttar Pradesh, India", offline_only=True)

    assert graph.graph["source"] == "offline_fallback"
    assert graph.graph["fallback_reason"] == "offline_only"


def test_offline_fallback_rejects_cities_without_a_matching_network():
    with pytest.raises(ValueError, match="only for Agra"):
        load_road_network("Delhi, India", offline_only=True)
