from __future__ import annotations

import math
import logging
import socket
from typing import Iterable, List, Tuple

import networkx as nx
import osmnx as ox


logger = logging.getLogger(__name__)
FALLBACK_CITY = "Agra, Uttar Pradesh, India"


def _fallback_graph(city_name: str, reason: str) -> nx.MultiDiGraph:
    if city_name.strip().casefold() not in {
        "agra",
        "agra, uttar pradesh",
        FALLBACK_CITY.casefold(),
    }:
        raise ValueError(
            f"The offline fallback network is available only for {FALLBACK_CITY}."
        )

    graph = nx.MultiDiGraph(name=f"Fallback road graph for {city_name}")
    graph.graph.update(
        source="offline_fallback",
        fallback_reason=reason,
        fallback_message={
            "offline_only": "The Agra offline fallback network was selected.",
            "openstreetmap_unreachable": "OpenStreetMap is unreachable; the Agra offline fallback is active.",
            "openstreetmap_load_failed": "OpenStreetMap could not load this network; the Agra offline fallback is active.",
        }[reason],
    )
    lat_center = 27.1767
    lon_center = 78.0081
    nodes = []
    for row in range(4):
        for col in range(4):
            lat = lat_center + (row - 1.5) * 0.005
            lon = lon_center + (col - 1.5) * 0.005
            nodes.append((lat, lon))
    node_ids = []
    for index, (lat, lon) in enumerate(nodes):
        node_ids.append(index)
        graph.add_node(index, x=lon, y=lat, lat=lat, lon=lon)

    for index in range(len(nodes) - 1):
        current = nodes[index]
        nxt = nodes[index + 1]
        if (index + 1) % 4 != 0:
            edge_data = {
                "key": 0,
                "length_m": 500.0,
                "road_type": "residential",
                "maxspeed": 30,
                "speed_kph": 30.0,
                "travel_time_minutes": 1.0,
            }
            graph.add_edge(index, index + 1, **edge_data)
            graph.add_edge(index + 1, index, **edge_data)
        if index < 12:
            edge_data = {
                "key": 0,
                "length_m": 600.0,
                "road_type": "primary",
                "maxspeed": 40,
                "speed_kph": 40.0,
                "travel_time_minutes": 1.2,
            }
            graph.add_edge(index, index + 4, **edge_data)
            graph.add_edge(index + 4, index, **edge_data)
    return graph


def _has_osm_access(host: str = "nominatim.openstreetmap.org", timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return True
    except (socket.timeout, OSError, ConnectionError):
        return False


def load_road_network(city_name: str, network_type: str = "drive", offline_only: bool = False) -> nx.MultiDiGraph:
    """Load a drivable road network for a selected city."""
    name = (city_name or "Agra, Uttar Pradesh, India").strip()
    if not name:
        raise ValueError("A city name is required.")

    if offline_only:
        return _fallback_graph(name, "offline_only")
    if not _has_osm_access():
        return _fallback_graph(name, "openstreetmap_unreachable")

    try:
        geocode = ox.geocode(name, timeout=5)
        if geocode is None:
            raise ValueError("City not found.")
        graph = ox.graph_from_place(name, network_type=network_type, simplify=True, timeout=10)
        if graph is None or graph.number_of_nodes() == 0:
            raise ValueError("No road network could be loaded for the provided city.")
        for _, _, _, data in graph.edges(data=True, keys=True):
            if "length" in data and "length_m" not in data:
                data["length_m"] = float(data["length"])
            if "speed_kph" not in data:
                data["speed_kph"] = 35.0
            if "travel_time_minutes" not in data:
                distance_km = (data.get("length_m", 0.0) / 1000.0)
                data["travel_time_minutes"] = max(0.1, (distance_km / max(data.get("speed_kph", 35.0), 1.0)) * 60.0)
        graph.graph["source"] = "openstreetmap"
        return graph
    except Exception as exc:
        logger.warning(
            "OSMnx network load failed for %s (%s); using the offline fallback when available.",
            name,
            type(exc).__name__,
        )
        return _fallback_graph(name, "openstreetmap_load_failed")


def snap_to_nearest_node(graph: nx.MultiDiGraph, latitude: float, longitude: float) -> int:
    if graph.number_of_nodes() == 0:
        raise ValueError("Road graph is empty so no location can be snapped.")

    best_node = None
    best_distance = math.inf
    for node, attributes in graph.nodes(data=True):
        node_lat = attributes.get("y")
        node_lon = attributes.get("x")
        if node_lat is None:
            node_lat = attributes.get("lat")
        if node_lon is None:
            node_lon = attributes.get("lon")
        if node_lat is None or node_lon is None:
            continue
        dist = (latitude - node_lat) ** 2 + (longitude - node_lon) ** 2
        if dist < best_distance:
            best_distance = dist
            best_node = node
    if best_node is None:
        raise ValueError("Unable to snap coordinates to any valid node in the graph.")
    return int(best_node)


def validate_coordinates(latitude: float, longitude: float) -> None:
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("Longitude must be between -180 and 180 degrees.")


def nearest_nodes(graph: nx.MultiDiGraph, points: Iterable[Tuple[float, float]]) -> List[int]:
    snapped = []
    for latitude, longitude in points:
        validate_coordinates(latitude, longitude)
        snapped.append(snap_to_nearest_node(graph, latitude, longitude))
    return snapped
