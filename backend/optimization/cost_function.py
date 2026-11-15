from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass
class ObjectiveWeights:
    distance: float = 0.5
    time: float = 0.3
    fuel: float = 0.2

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.distance, self.time, self.fuel)

    def validate(self) -> None:
        total = self.distance + self.time + self.fuel
        if any(not math.isfinite(value) for value in (self.distance, self.time, self.fuel)):
            raise ValueError("Objective weights must be finite.")
        if total <= 0:
            raise ValueError("Objective weights must sum to a positive value.")
        if any(value < 0 for value in (self.distance, self.time, self.fuel)):
            raise ValueError("Objective weights cannot be negative.")


@dataclass
class RouteMetrics:
    distance_km: float
    travel_time_minutes: float
    fuel_liters: float
    combined_cost: float


def _normalize(value: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0 if value <= 0 else 1.0
    return value / baseline


def compute_combined_cost(
    distance_km: float,
    travel_time_minutes: float,
    fuel_liters: float,
    weights: ObjectiveWeights | Sequence[float] | None = None,
    normalization_baseline: tuple[float, float, float] | None = None,
) -> tuple[float, float, float, float]:
    metric_values = (distance_km, travel_time_minutes, fuel_liters)
    if any(not math.isfinite(value) or value < 0 for value in metric_values):
        raise ValueError("Route metrics must be finite and non-negative.")
    if weights is None:
        weights = ObjectiveWeights()
    if isinstance(weights, ObjectiveWeights):
        weight_values = weights.as_tuple()
    else:
        weight_values = tuple(float(value) for value in weights)
        if len(weight_values) != 3:
            raise ValueError("Weight sequence must contain exactly three values.")

    total = sum(weight_values)
    if any(not math.isfinite(value) for value in weight_values):
        raise ValueError("Objective weights must be finite.")
    if total <= 0:
        raise ValueError("Objective weights must sum to a positive value.")
    if any(value < 0 for value in weight_values):
        raise ValueError("Objective weights cannot be negative.")

    if normalization_baseline is None:
        normalization_baseline = (1.0, 1.0, 1.0)
    if any(not math.isfinite(value) or value < 0 for value in normalization_baseline):
        raise ValueError("Normalization baselines must be finite and non-negative.")

    dist_normalized = _normalize(distance_km, normalization_baseline[0])
    time_normalized = _normalize(travel_time_minutes, normalization_baseline[1])
    fuel_normalized = _normalize(fuel_liters, normalization_baseline[2])

    combined = (
        weight_values[0] * dist_normalized
        + weight_values[1] * time_normalized
        + weight_values[2] * fuel_normalized
    ) / total
    return dist_normalized, time_normalized, fuel_normalized, combined


def evaluate_route_metrics(
    distance_km: float,
    travel_time_minutes: float,
    fuel_liters: float,
    weights: ObjectiveWeights | Sequence[float] | None = None,
    normalization_baseline: tuple[float, float, float] | None = None,
) -> RouteMetrics:
    dist_norm, time_norm, fuel_norm, combined = compute_combined_cost(
        distance_km,
        travel_time_minutes,
        fuel_liters,
        weights=weights,
        normalization_baseline=normalization_baseline,
    )
    return RouteMetrics(
        distance_km=distance_km,
        travel_time_minutes=travel_time_minutes,
        fuel_liters=fuel_liters,
        combined_cost=combined,
    )
