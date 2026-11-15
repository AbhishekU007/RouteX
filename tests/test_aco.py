import numpy as np
import pytest

from algorithms.aco import ACOConfig, AntColonyOptimizer


def test_aco_generates_valid_route():
    cost_matrix = np.array([
        [0.0, 5.0, 7.0, 9.0],
        [5.0, 0.0, 2.0, 6.0],
        [7.0, 2.0, 0.0, 3.0],
        [9.0, 6.0, 3.0, 0.0],
    ])
    optimizer = AntColonyOptimizer(ACOConfig(num_ants=10, iterations=10, random_seed=7))
    result = optimizer.optimize(cost_matrix)
    route = result.route
    assert route[0] == 0
    assert route[-1] == 0
    assert sorted(route[1:-1]) == [1, 2, 3]
    assert len(route) == 5


def test_pheromone_values_are_valid():
    cost_matrix = np.array([
        [0.0, 4.0, 3.0],
        [4.0, 0.0, 2.0],
        [3.0, 2.0, 0.0],
    ])
    result = AntColonyOptimizer(ACOConfig(iterations=5, random_seed=1)).optimize(cost_matrix)
    assert result.pheromone is not None
    assert np.all(np.isfinite(result.pheromone))
    assert np.all(result.pheromone >= 0)
    np.fill_diagonal(result.pheromone, 0.0)


def test_aco_rejects_unreachable_transitions_instead_of_returning_invalid_route():
    cost_matrix = np.array([
        [0.0, 1.0, np.inf],
        [1.0, 0.0, np.inf],
        [np.inf, np.inf, 0.0],
    ])

    with pytest.raises(ValueError, match="No feasible route"):
        AntColonyOptimizer(ACOConfig(num_ants=8, iterations=10, random_seed=2)).optimize(cost_matrix)


def test_aco_open_route_visits_required_nodes_and_ends_at_fixed_depot_node():
    cost_matrix = np.array([
        [0.0, 2.0, 3.0, 2.0],
        [2.0, 0.0, 1.0, 2.0],
        [3.0, 1.0, 0.0, 2.0],
        [2.0, 2.0, 2.0, 0.0],
    ])

    result = AntColonyOptimizer(ACOConfig(random_seed=9)).optimize(cost_matrix, end_node=3)

    assert result.route[0] == 0
    assert result.route[-1] == 3
    assert sorted(result.route[1:-1]) == [1, 2]
    assert np.isfinite(result.cost)


def test_aco_rejects_invalid_parameters_and_costs():
    with pytest.raises(ValueError, match="evaporation_rate"):
        AntColonyOptimizer(ACOConfig(evaporation_rate=1.0))
    with pytest.raises(ValueError, match="cost_matrix values"):
        AntColonyOptimizer().optimize([[0.0, -1.0], [1.0, 0.0]])


def test_random_seed_reproduces_aco_history_and_route():
    matrix = np.array([
        [0.0, 2.0, 3.0, 5.0],
        [2.0, 0.0, 4.0, 1.0],
        [3.0, 4.0, 0.0, 2.0],
        [5.0, 1.0, 2.0, 0.0],
    ])
    config = ACOConfig(num_ants=10, iterations=10, random_seed=123)

    first = AntColonyOptimizer(config).optimize(matrix)
    second = AntColonyOptimizer(config).optimize(matrix)

    assert first.route == second.route
    assert first.history == second.history


def test_pheromone_update_evaporates_then_reinforces_route_edges():
    optimizer = AntColonyOptimizer(ACOConfig(evaporation_rate=0.2))
    pheromone = np.ones((3, 3), dtype=float)
    np.fill_diagonal(pheromone, 0.0)
    route = [0, 1, 2, 0]

    updated = optimizer._evaporate_and_deposit(pheromone, [(route, 2.0)], route, 2.0)

    assert np.isclose(updated[0, 1], 1.8)
    assert np.isclose(updated[1, 2], 1.8)
    assert np.isclose(updated[0, 2], 0.8)
