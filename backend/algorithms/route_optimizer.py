from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

import math

import numpy as np

from algorithms.aco import ACOConfig, AntColonyOptimizer
from network.distance_matrix import compute_route_cost_matrix
from optimization.cost_function import ObjectiveWeights, evaluate_route_metrics


def _objective_scales(matrices: dict) -> tuple[float, float, float]:
    scales = []
    for key in ("distance_km", "travel_time_minutes", "fuel_liters"):
        matrix = np.asarray(matrices[key], dtype=float)
        values = matrix[np.isfinite(matrix) & (matrix > 0)]
        scales.append(float(np.median(values)) if values.size else 1.0)
    return scales[0], scales[1], scales[2]


def _build_objective_matrix(
    matrices: dict,
    weights: ObjectiveWeights,
    normalization_baseline: tuple[float, float, float] | None = None,
) -> tuple[np.ndarray, tuple[float, float, float]]:
    weights.validate()
    weight_total = sum(weights.as_tuple())
    normalized_weights = tuple(value / weight_total for value in weights.as_tuple())
    scales = normalization_baseline or _objective_scales(matrices)
    if any(not math.isfinite(scale) or scale <= 0 for scale in scales):
        raise ValueError("Objective normalization scales must be finite and positive.")
    distance = np.asarray(matrices["distance_km"], dtype=float)
    travel_time = np.asarray(matrices["travel_time_minutes"], dtype=float)
    fuel = np.asarray(matrices["fuel_liters"], dtype=float)
    if distance.shape != travel_time.shape or distance.shape != fuel.shape:
        raise ValueError("Distance, time, and fuel matrices must have matching shapes.")
    reachable = np.isfinite(distance) & np.isfinite(travel_time) & np.isfinite(fuel)
    objective = np.full(distance.shape, np.inf, dtype=float)
    objective[reachable] = (
        normalized_weights[0] * distance[reachable] / scales[0]
        + normalized_weights[1] * travel_time[reachable] / scales[1]
        + normalized_weights[2] * fuel[reachable] / scales[2]
    )
    np.fill_diagonal(objective, 0.0)
    return objective, scales


@dataclass
class RouteOptimizationResult:
    route: List[int]
    original_route: List[int] | None = None
    metrics: Dict[str, float] = field(default_factory=dict)
    history: List[float] = field(default_factory=list)
    mode: str = "initial"
    stop_order: List[int] | None = None
    start_position: tuple[float, float] | None = None
    normalization_baseline: tuple[float, float, float] | None = None


class RouteOptimizer:
    def __init__(self, graph: Any, depot: tuple[float, float], stops: Sequence[tuple[float, float]], config: ACOConfig | None = None):
        self.graph = graph
        self.depot = depot
        self.stops = list(stops)
        self.config = config or ACOConfig()

    def optimize(
        self,
        traffic_factor: float = 1.0,
        congestion_multiplier: float = 1.0,
        mileage_km_per_litre: float = 12.0,
        weights: ObjectiveWeights | None = None,
        normalization_baseline: tuple[float, float, float] | None = None,
    ) -> RouteOptimizationResult:
        weights = weights or ObjectiveWeights()
        matrices = compute_route_cost_matrix(
            self.graph,
            self.depot,
            self.stops,
            mileage_km_per_litre=mileage_km_per_litre,
            traffic_factor=traffic_factor,
            congestion_multiplier=congestion_multiplier,
        )

        n = len(self.stops) + 1
        distance_matrix = matrices["distance_km"]
        if distance_matrix.shape[0] <= 1:
            route = [0]
            metrics = {"distance_km": 0.0, "travel_time_minutes": 0.0, "fuel_liters": 0.0}
            return RouteOptimizationResult(route=route, metrics=metrics, history=[], mode="initial")

        objective_matrix, scales = _build_objective_matrix(
            matrices,
            weights,
            normalization_baseline=normalization_baseline,
        )
        optimizer = AntColonyOptimizer(self.config)
        result = optimizer.optimize(objective_matrix)
        sequence = result.route

        distance = 0.0
        travel_time = 0.0
        fuel = 0.0
        for left, right in zip(sequence, sequence[1:]):
            distance += float(distance_matrix[left, right])
            travel_time += float(matrices["travel_time_minutes"][left, right])
            fuel += float(matrices["fuel_liters"][left, right])

        metric_obj = evaluate_route_metrics(
            distance,
            travel_time,
            fuel,
            weights=weights,
            normalization_baseline=scales,
        )
        return RouteOptimizationResult(
            route=sequence,
            metrics={
                "distance_km": distance,
                "travel_time_minutes": travel_time,
                "fuel_liters": fuel,
                "combined_cost": metric_obj.combined_cost,
            },
            history=result.history,
            mode="initial",
            normalization_baseline=scales,
        )

    def replan_remaining(
        self,
        completed: Sequence[int],
        traffic_factor: float = 1.0,
        congestion_multiplier: float = 1.0,
        mileage_km_per_litre: float = 12.0,
        min_improvement: float = 0.05,
        current_position: tuple[float, float] | None = None,
        weights: ObjectiveWeights | None = None,
    ) -> RouteOptimizationResult:
        if len(set(completed)) != len(completed) or any(index < 0 or index >= len(self.stops) for index in completed):
            raise ValueError("Completed delivery indices must be unique valid stop indices.")
        remaining_ids = [i for i in range(len(self.stops)) if i not in completed]
        remaining = [self.stops[i] for i in remaining_ids]
        start = current_position or self.depot
        if not remaining:
            matrices = compute_route_cost_matrix(
                self.graph,
                start,
                [self.depot],
                mileage_km_per_litre=mileage_km_per_litre,
                traffic_factor=traffic_factor,
                congestion_multiplier=congestion_multiplier,
            )
            distance = float(matrices["distance_km"][0, 1])
            travel_time = float(matrices["travel_time_minutes"][0, 1])
            fuel = float(matrices["fuel_liters"][0, 1])
            if not all(math.isfinite(value) for value in (distance, travel_time, fuel)):
                raise ValueError("No road path connects the current position to the depot.")
            weights = weights or ObjectiveWeights()
            scales = _objective_scales(matrices)
            combined_cost = evaluate_route_metrics(
                distance,
                travel_time,
                fuel,
                weights=weights,
                normalization_baseline=scales,
            ).combined_cost
            return RouteOptimizationResult(
                route=[0, 1],
                metrics={
                    "distance_km": distance,
                    "travel_time_minutes": travel_time,
                    "fuel_liters": fuel,
                    "combined_cost": combined_cost,
                },
                history=[],
                mode="dynamic",
                stop_order=[],
                start_position=start,
                normalization_baseline=scales,
            )

        weights = weights or ObjectiveWeights()
        matrices = compute_route_cost_matrix(
            self.graph,
            start,
            [*remaining, self.depot],
            mileage_km_per_litre=mileage_km_per_litre,
            traffic_factor=traffic_factor,
            congestion_multiplier=congestion_multiplier,
        )
        objective, scales = _build_objective_matrix(matrices, weights)
        end_node = len(remaining) + 1
        aco_result = AntColonyOptimizer(self.config).optimize(objective, end_node=end_node)
        distance = sum(float(matrices["distance_km"][a, b]) for a, b in zip(aco_result.route, aco_result.route[1:]))
        travel_time = sum(float(matrices["travel_time_minutes"][a, b]) for a, b in zip(aco_result.route, aco_result.route[1:]))
        fuel = sum(float(matrices["fuel_liters"][a, b]) for a, b in zip(aco_result.route, aco_result.route[1:]))
        metric_obj = evaluate_route_metrics(distance, travel_time, fuel, weights=weights, normalization_baseline=scales)
        order = [remaining_ids[index - 1] for index in aco_result.route[1:-1]]
        return RouteOptimizationResult(
            route=aco_result.route,
            metrics={
                "distance_km": distance,
                "travel_time_minutes": travel_time,
                "fuel_liters": fuel,
                "combined_cost": metric_obj.combined_cost,
            },
            history=aco_result.history,
            mode="dynamic",
            stop_order=order,
            start_position=start,
            normalization_baseline=scales,
        )
