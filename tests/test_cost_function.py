import numpy as np

from algorithms.aco import ACOConfig, AntColonyOptimizer
from algorithms.route_optimizer import _build_objective_matrix
from optimization.cost_function import ObjectiveWeights, compute_combined_cost


def test_cost_function_normalizes_and_combines_metrics():
    dist_norm, time_norm, fuel_norm, combined = compute_combined_cost(100.0, 80.0, 20.0, weights=(0.5, 0.3, 0.2))
    assert (dist_norm, time_norm, fuel_norm) == (100.0, 80.0, 20.0)
    assert combined == 78.0


def test_invalid_weights_are_rejected():
    try:
        compute_combined_cost(10.0, 10.0, 10.0, weights=(-1.0, 1.0, 1.0))
        raise AssertionError("Expected ValueError for invalid weights.")
    except ValueError:
        pass


def test_objective_weights_sum_to_one_is_optional_but_valid():
    weights = ObjectiveWeights(distance=0.5, time=0.3, fuel=0.2)
    metrics = compute_combined_cost(50, 30, 10, weights=weights)
    assert metrics[-1] >= 0


def test_distance_and_time_weights_change_the_preferred_route():
    distance = np.full((4, 4), 100.0)
    travel_time = np.full((4, 4), 100.0)
    fuel = np.full((4, 4), 100.0)
    np.fill_diagonal(distance, 0.0)
    np.fill_diagonal(travel_time, 0.0)
    np.fill_diagonal(fuel, 0.0)

    distance_route = [(0, 1), (1, 2), (2, 3), (3, 0)]
    time_route = [(0, 2), (2, 1), (1, 3), (3, 0)]
    for left, right in distance_route[:-1]:
        distance[left, right] = 1.0
        travel_time[left, right] = 10.0
        fuel[left, right] = 1.0
    for left, right in time_route[:-1]:
        distance[left, right] = 10.0
        travel_time[left, right] = 1.0
        fuel[left, right] = 10.0
    distance[3, 0] = travel_time[3, 0] = fuel[3, 0] = 1.0
    matrices = {
        "distance_km": distance,
        "travel_time_minutes": travel_time,
        "fuel_liters": fuel,
    }

    def optimize(weights):
        objective, _ = _build_objective_matrix(matrices, weights)
        return AntColonyOptimizer(ACOConfig(num_ants=40, iterations=60, random_seed=3)).optimize(objective).route

    shortest_by_distance = optimize(ObjectiveWeights(distance=1, time=0, fuel=0))
    shortest_by_time = optimize(ObjectiveWeights(distance=0, time=1, fuel=0))

    assert shortest_by_distance == [0, 1, 2, 3, 0]
    assert shortest_by_time == [0, 2, 1, 3, 0]


def test_combined_cost_is_finite_for_zero_metrics_and_normalized_weights():
    _, _, _, combined = compute_combined_cost(0.0, 0.0, 0.0, weights=(2.0, 3.0, 5.0))
    assert np.isfinite(combined)
    assert combined == 0.0
