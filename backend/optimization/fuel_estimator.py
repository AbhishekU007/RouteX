from __future__ import annotations


def estimate_fuel_consumption(
    distance_km: float,
    mileage_km_per_litre: float = 12.0,
    traffic_factor: float = 1.0,
    congestion_multiplier: float = 1.0,
) -> float:
    """Estimate fuel consumption for a route using an adjustable traffic factor."""
    if distance_km < 0:
        raise ValueError("Distance cannot be negative.")
    if mileage_km_per_litre <= 0:
        raise ValueError("Vehicle mileage must be positive.")
    if traffic_factor <= 0:
        raise ValueError("Traffic factor must be positive.")
    if congestion_multiplier <= 0:
        raise ValueError("Congestion multiplier must be positive.")

    adjusted_distance = distance_km * traffic_factor * congestion_multiplier
    return max(0.0, adjusted_distance / mileage_km_per_litre)
