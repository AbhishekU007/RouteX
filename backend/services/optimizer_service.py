from __future__ import annotations

import asyncio
import copy
import threading
import uuid
from typing import Any

import networkx as nx

from algorithms.aco import ACOConfig
from algorithms.route_optimizer import RouteOptimizer
from models.schemas import OptimizationRequest, ReplanRequest, TrafficSimulationRequest
from network.distance_matrix import compute_route_cost_matrix
from network.road_network import load_road_network
from optimization.cost_function import ObjectiveWeights
from traffic.traffic_simulator import TrafficSimulator
from utils.config import DEFAULT_CITY


def default_sample_stops() -> list[tuple[float, float]]:
    return [
        (27.1779, 78.0101),
        (27.1754, 78.0130),
        (27.1733, 78.0076),
        (27.1784, 78.0052),
    ]


STATE: dict[str, Any] = {
    "city": DEFAULT_CITY,
    "network": load_road_network(DEFAULT_CITY, offline_only=True),
    "depot": (27.1767, 78.0081),
    "stops": default_sample_stops(),
    "route_result": None,
    "original_route_result": None,
    "latest_replanned_route": None,
    "traffic_comparison": {
        "normal_traffic_baseline": None,
        "simulated_congestion_scenario": None,
    },
    "route_history": [],
    "traffic_simulator": TrafficSimulator(seed=42),
    "traffic_status": {"source": "simulated", "available": False, "status": "normal", "city": DEFAULT_CITY},
    "job_store": {},
}


def _route_geometry(graph: nx.MultiDiGraph, route_nodes: list[int]) -> list[list[float]]:
    coords: list[list[float]] = []
    if len(route_nodes) < 2:
        return coords
    for left_node, right_node in zip(route_nodes, route_nodes[1:]):
        if left_node == right_node:
            continue
        try:
            path = nx.shortest_path(graph, left_node, right_node, weight="length_m")
        except nx.NetworkXNoPath:
            continue
        for source, target in zip(path, path[1:]):
            edge_data = graph.get_edge_data(source, target) or {}
            if not edge_data:
                continue
            selected = min(
                edge_data.values(),
                key=lambda data: float(data.get("length_m", data.get("length", 0.0))),
            )
            geometry = selected.get("geometry")
            if geometry is not None and hasattr(geometry, "coords"):
                points = list(geometry.coords)
                source_attrs = graph.nodes[source]
                target_attrs = graph.nodes[target]
                source_xy = (float(source_attrs.get("x", 0.0)), float(source_attrs.get("y", 0.0)))
                target_xy = (float(target_attrs.get("x", 0.0)), float(target_attrs.get("y", 0.0)))
                if points:
                    first_xy = points[0]
                    last_xy = points[-1]
                    direct_error = (
                        (first_xy[0] - source_xy[0]) ** 2 + (first_xy[1] - source_xy[1]) ** 2
                        + (last_xy[0] - target_xy[0]) ** 2 + (last_xy[1] - target_xy[1]) ** 2
                    )
                    reverse_error = (
                        (last_xy[0] - source_xy[0]) ** 2 + (last_xy[1] - source_xy[1]) ** 2
                        + (first_xy[0] - target_xy[0]) ** 2 + (first_xy[1] - target_xy[1]) ** 2
                    )
                    if reverse_error < direct_error:
                        points.reverse()
                edge_coords = [[float(latitude), float(longitude)] for longitude, latitude, *rest in points]
            else:
                edge_coords = []
                for node in (source, target):
                    attrs = graph.nodes[node]
                    latitude = float(attrs.get("y", attrs.get("lat", 0.0)))
                    longitude = float(attrs.get("x", attrs.get("lon", 0.0)))
                    edge_coords.append([latitude, longitude])
            if coords and edge_coords and coords[-1] == edge_coords[0]:
                edge_coords = edge_coords[1:]
            coords.extend(edge_coords)
    return coords


def _sequence_from_route(route: list[int], stops: list[tuple[float, float]]) -> list[dict[str, Any]]:
    sequence: list[dict[str, Any]] = []
    for position, value in enumerate(route):
        if value == 0:
            sequence.append({"position": position, "type": "depot", "latitude": STATE["depot"][0], "longitude": STATE["depot"][1]})
            continue
        if value <= len(stops):
            stop_index = value - 1
            stop = stops[stop_index]
            sequence.append({
                "position": position,
                "type": "stop",
                "index": stop_index,
                "latitude": stop[0],
                "longitude": stop[1],
                "label": f"Stop {stop_index + 1}",
            })
    return sequence


def _as_route_payload(result: Any, graph: nx.MultiDiGraph, depot: tuple[float, float], stops: list[tuple[float, float]], mileage: float, traffic_factor: float, congestion_multiplier: float) -> dict[str, Any]:
    matrices = compute_route_cost_matrix(graph, depot, stops, mileage_km_per_litre=mileage, traffic_factor=traffic_factor, congestion_multiplier=congestion_multiplier)
    snapped_nodes = matrices["nodes"]
    route_nodes = [snapped_nodes[index] for index in result.route]
    payload = {
        "route": result.route,
        "route_nodes": route_nodes,
        "metrics": result.metrics,
        "history": result.history,
        "mode": result.mode,
        "geometry": _route_geometry(graph, route_nodes),
        "sequence": _sequence_from_route(result.route, stops),
    }
    return payload


def _as_replan_payload(
    result: Any,
    graph: nx.MultiDiGraph,
    depot: tuple[float, float],
    stops: list[tuple[float, float]],
    completed: list[int],
    mileage: float,
    traffic_factor: float,
    congestion_multiplier: float,
) -> dict[str, Any]:
    start = result.start_position or depot
    remaining_ids = [index for index in range(len(stops)) if index not in completed]
    matrices = compute_route_cost_matrix(
        graph,
        start,
        [*[stops[index] for index in remaining_ids], depot],
        mileage_km_per_litre=mileage,
        traffic_factor=traffic_factor,
        congestion_multiplier=congestion_multiplier,
    )
    route_nodes = [matrices["nodes"][index] for index in result.route]
    sequence: list[dict[str, Any]] = [
        {"position": 0, "type": "current", "latitude": start[0], "longitude": start[1]}
    ]
    for position, stop_index in enumerate(result.stop_order or [], start=1):
        latitude, longitude = stops[stop_index]
        sequence.append({
            "position": position,
            "type": "stop",
            "index": stop_index,
            "latitude": latitude,
            "longitude": longitude,
            "label": f"Stop {stop_index + 1}",
        })
    sequence.append({
        "position": len(sequence),
        "type": "depot",
        "latitude": depot[0],
        "longitude": depot[1],
    })
    return {
        "route": result.route,
        "route_nodes": route_nodes,
        "route_stop_indices": result.stop_order or [],
        "metrics": result.metrics,
        "history": result.history,
        "mode": result.mode,
        "geometry": _route_geometry(graph, route_nodes),
        "sequence": sequence,
        "current_position": {"latitude": start[0], "longitude": start[1]},
    }


def set_network(city: str, offline_only: bool = True) -> dict[str, Any]:
    state_network = load_road_network(city, offline_only=offline_only)
    previous_network = STATE["network"]
    STATE["traffic_simulator"].clear_congestion(previous_network)
    STATE["city"] = city
    STATE["network"] = state_network
    STATE["traffic_status"] = {
        "source": "simulated",
        "available": False,
        "status": "normal",
        "city": city,
    }
    STATE["route_result"] = None
    STATE["original_route_result"] = None
    STATE["latest_replanned_route"] = None
    STATE["route_history"] = []
    STATE["traffic_comparison"] = {
        "normal_traffic_baseline": None,
        "simulated_congestion_scenario": None,
    }
    return {
        "status": "ready",
        "city": city,
        "nodes": state_network.number_of_nodes(),
        "edges": state_network.number_of_edges(),
        "loaded": True,
        "source": state_network.graph.get("source", "unknown"),
        "fallback_reason": state_network.graph.get("fallback_reason"),
        "fallback_message": state_network.graph.get("fallback_message"),
    }


def get_network_status() -> dict[str, Any]:
    graph = STATE.get("network")
    if graph is None:
        return {
            "status": "unavailable",
            "city": STATE["city"],
            "nodes": 0,
            "edges": 0,
            "source": "unavailable",
        }
    return {
        "status": "ready" if graph.number_of_nodes() > 0 else "unavailable",
        "city": STATE["city"],
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "source": graph.graph.get("source", "unknown"),
        "fallback_reason": graph.graph.get("fallback_reason"),
        "fallback_message": graph.graph.get("fallback_message"),
    }


def set_locations(depot: tuple[float, float] | None = None, stops: list[tuple[float, float]] | None = None) -> dict[str, Any]:
    if depot is not None:
        STATE["depot"] = depot
    if stops is not None:
        STATE["stops"] = stops
    return {"depot": STATE["depot"], "stops": STATE["stops"]}


def get_locations() -> dict[str, Any]:
    return {"city": STATE["city"], "depot": STATE["depot"], "stops": STATE["stops"]}


def optimize_route(request: OptimizationRequest) -> dict[str, Any]:
    if request.city.strip().casefold() != STATE["city"].strip().casefold():
        raise ValueError("Load the road network for the selected city before optimizing.")

    depot = tuple(request.depot)
    stops = [tuple(stop) for stop in request.stops]
    STATE["depot"] = depot
    STATE["stops"] = stops
    config = ACOConfig(
        num_ants=request.config.num_ants,
        alpha=request.config.alpha,
        beta=request.config.beta,
        evaporation_rate=request.config.evaporation_rate,
        iterations=request.config.iterations,
        random_seed=request.config.random_seed,
    )
    optimizer = RouteOptimizer(STATE["network"], depot, stops, config=config)
    result = optimizer.optimize(
        traffic_factor=request.config.traffic_factor,
        congestion_multiplier=request.config.congestion_multiplier,
        mileage_km_per_litre=request.config.mileage_km_per_litre,
        weights=ObjectiveWeights(
            distance=request.config.distance_weight,
            time=request.config.time_weight,
            fuel=request.config.fuel_weight,
        ),
    )
    result_payload = _as_route_payload(
        result,
        STATE["network"],
        depot,
        stops,
        request.config.mileage_km_per_litre,
        request.config.traffic_factor,
        request.config.congestion_multiplier,
    )
    STATE["route_result"] = result_payload
    STATE["original_route_result"] = result_payload
    STATE["latest_replanned_route"] = None
    STATE["traffic_comparison"]["normal_traffic_baseline"] = (
        copy.deepcopy(result_payload)
        if STATE["traffic_status"].get("status") == "normal"
        else None
    )
    STATE["traffic_comparison"]["simulated_congestion_scenario"] = None
    STATE["route_history"].append({
        "timestamp": "now",
        "metrics": result_payload["metrics"],
        "mode": result_payload["mode"],
    })
    return result_payload


async def _run_optimization_job(job_id: str, request: OptimizationRequest) -> None:
    STATE["job_store"][job_id] = {"status": "running", "progress": 20, "message": "Optimizing route..."}
    try:
        result = optimize_route(request)
        STATE["job_store"][job_id] = {"status": "completed", "progress": 100, "message": "Optimization complete", "result": result}
    except Exception as exc:  # pragma: no cover - runtime guard
        STATE["job_store"][job_id] = {"status": "failed", "progress": 100, "message": f"Optimization failed: {exc}", "result": None}


def enqueue_optimization(request: OptimizationRequest) -> str:
    job_id = uuid.uuid4().hex
    STATE["job_store"][job_id] = {"status": "queued", "progress": 5, "message": "Queued for optimization"}

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        def _runner() -> None:
            asyncio.run(_run_optimization_job(job_id, request))

        threading.Thread(target=_runner, daemon=True).start()
    else:
        loop.create_task(_run_optimization_job(job_id, request))

    return job_id


def get_job_status(job_id: str) -> dict[str, Any]:
    return STATE["job_store"].get(job_id, {"status": "failed", "progress": 0, "message": "Unknown job"})


def get_route_history() -> list[dict[str, Any]]:
    return STATE["route_history"]


def get_current_route() -> dict[str, Any] | None:
    return STATE["route_result"]


def simulate_traffic(payload: TrafficSimulationRequest) -> dict[str, Any]:
    graph = STATE["network"]
    STATE["traffic_simulator"].clear_congestion(graph)
    STATE["traffic_simulator"].apply_random_congestion(graph, level=payload.level, fraction=payload.fraction)
    STATE["traffic_simulator"].update_all_travel_times(graph)
    STATE["traffic_status"] = {
        "source": "simulated",
        "available": False,
        "status": payload.level,
        "city": STATE["city"],
        "message": f"Simulated traffic updated to {payload.level}; edge travel times were recalculated.",
    }
    return STATE["traffic_status"]


def reset_traffic() -> dict[str, Any]:
    STATE["traffic_simulator"].clear_congestion(STATE["network"])
    STATE["traffic_simulator"].update_all_travel_times(STATE["network"])
    STATE["traffic_status"] = {
        "source": "simulated",
        "available": False,
        "status": "normal",
        "city": STATE["city"],
    }
    return STATE["traffic_status"]


def get_traffic_status() -> dict[str, Any]:
    return STATE["traffic_status"]


def replan_remaining(request: ReplanRequest) -> dict[str, Any]:
    completed = request.completed
    if len(set(completed)) != len(completed) or any(index < 0 or index >= len(STATE["stops"]) for index in completed):
        raise ValueError("Completed delivery indices must be unique valid stop indices.")
    completed_set = set(completed)
    active_sequence = (STATE["route_result"] or {}).get("sequence", [])
    completed_in_route_order = [
        entry["index"]
        for entry in active_sequence
        if entry.get("type") == "stop" and entry.get("index") in completed_set
    ]
    ordered_completed = completed_in_route_order or completed
    current_position = STATE["depot"] if not ordered_completed else STATE["stops"][ordered_completed[-1]]
    previous_metrics = (STATE["route_result"] or {}).get("metrics")
    optimizer = RouteOptimizer(
        STATE["network"],
        STATE["depot"],
        STATE["stops"],
        config=ACOConfig(
            num_ants=request.config.num_ants,
            alpha=request.config.alpha,
            beta=request.config.beta,
            evaporation_rate=request.config.evaporation_rate,
            iterations=request.config.iterations,
            random_seed=request.config.random_seed,
        ),
    )
    result = optimizer.replan_remaining(
        completed=completed,
        traffic_factor=request.config.traffic_factor,
        congestion_multiplier=request.config.congestion_multiplier,
        mileage_km_per_litre=request.config.mileage_km_per_litre,
        current_position=current_position,
        weights=ObjectiveWeights(
            distance=request.config.distance_weight,
            time=request.config.time_weight,
            fuel=request.config.fuel_weight,
        ),
    )
    result_payload = _as_replan_payload(
        result,
        STATE["network"],
        STATE["depot"],
        STATE["stops"],
        completed,
        request.config.mileage_km_per_litre,
        request.config.traffic_factor,
        request.config.congestion_multiplier,
    )
    result_payload["previous_metrics"] = previous_metrics
    result_payload["original_route"] = STATE["original_route_result"]
    result_payload["completed_stop_indices"] = list(completed)
    STATE["route_result"] = result_payload
    STATE["latest_replanned_route"] = copy.deepcopy(result_payload)
    STATE["route_history"].append({"timestamp": "now", "metrics": result_payload["metrics"], "mode": "replan"})
    if STATE["traffic_status"].get("status") == "normal":
        if STATE["traffic_comparison"].get("normal_traffic_baseline") is None:
            STATE["traffic_comparison"]["normal_traffic_baseline"] = copy.deepcopy(result_payload)
    else:
        STATE["traffic_comparison"]["simulated_congestion_scenario"] = {
            "traffic_status": copy.deepcopy(STATE["traffic_status"]),
            "route": copy.deepcopy(result_payload),
        }
    return result_payload


def get_analytics() -> dict[str, Any]:
    route = STATE["route_result"]
    if route is None:
        return {
            "distance_km": None,
            "travel_time_minutes": None,
            "fuel_liters": None,
            "history": [],
            "original_complete_route": None,
            "active_route": None,
            "replanned_route": None,
            **copy.deepcopy(STATE["traffic_comparison"]),
        }
    return {
        "distance_km": route["metrics"].get("distance_km", 0.0),
        "travel_time_minutes": route["metrics"].get("travel_time_minutes", 0.0),
        "fuel_liters": route["metrics"].get("fuel_liters", 0.0),
        "history": STATE["route_history"],
        "original_complete_route": copy.deepcopy(STATE["original_route_result"]),
        "active_route": copy.deepcopy(route),
        "replanned_route": copy.deepcopy(STATE["latest_replanned_route"]),
        **copy.deepcopy(STATE["traffic_comparison"]),
    }
