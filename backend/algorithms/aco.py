from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np


@dataclass
class ACOConfig:
    num_ants: int = 20
    alpha: float = 1.0
    beta: float = 3.0
    evaporation_rate: float = 0.2
    iterations: int = 40
    initial_pheromone: float = 1.0
    random_seed: int = 42


@dataclass
class ACOResult:
    route: List[int]
    cost: float
    history: List[float] = field(default_factory=list)
    pheromone: np.ndarray | None = None


class AntColonyOptimizer:
    """A compact, custom ant colony optimizer for TSP-like route sequencing."""

    def __init__(self, config: ACOConfig | None = None):
        self.config = config or ACOConfig()
        if self.config.num_ants <= 0 or self.config.iterations <= 0:
            raise ValueError("num_ants and iterations must be positive.")
        if not math.isfinite(self.config.alpha) or not 0 <= self.config.alpha <= 100:
            raise ValueError("alpha must be finite and in [0, 100].")
        if not math.isfinite(self.config.beta) or not 0 <= self.config.beta <= 100:
            raise ValueError("beta must be finite and in [0, 100].")
        if not math.isfinite(self.config.evaporation_rate) or not 0 <= self.config.evaporation_rate < 1:
            raise ValueError("evaporation_rate must be in [0, 1).")
        if not math.isfinite(self.config.initial_pheromone) or self.config.initial_pheromone <= 0:
            raise ValueError("initial_pheromone must be finite and positive.")
        self.rand = random.Random(self.config.random_seed)

    def optimize(self, cost_matrix: Sequence[Sequence[float]], end_node: int | None = None) -> ACOResult:
        matrix = np.asarray(cost_matrix, dtype=float)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ValueError("cost_matrix must be a square 2D matrix.")
        if matrix.shape[0] == 0:
            raise ValueError("cost_matrix must contain at least one node.")
        if np.isnan(matrix).any() or np.isneginf(matrix).any() or np.any(matrix[np.isfinite(matrix)] < 0):
            raise ValueError("cost_matrix values must be non-negative finite values or positive infinity.")
        n = matrix.shape[0]
        if end_node is not None and (end_node <= 0 or end_node >= n):
            raise ValueError("end_node must identify a non-depot node in the cost matrix.")
        if n <= 1:
            return ACOResult(route=[0], cost=0.0, history=[0.0], pheromone=np.zeros((1, 1)))

        pheromone = np.full((n, n), self.config.initial_pheromone, dtype=float)
        pheromone[~np.isfinite(matrix)] = 0.0
        np.fill_diagonal(pheromone, 0.0)
        best_route: List[int] | None = None
        best_cost = float("inf")
        history: List[float] = []

        for _ in range(self.config.iterations):
            candidate_routes = []
            for _ in range(self.config.num_ants):
                route = self._construct_route(matrix, pheromone, end_node=end_node)
                if route is None:
                    continue
                route_cost = self._route_cost(route, matrix, end_node=end_node)
                if not math.isfinite(route_cost):
                    continue
                candidate_routes.append((route, route_cost))

            if not candidate_routes:
                if best_route is None:
                    raise ValueError("No feasible route visits every required node and returns to the depot.")
                break

            candidate_routes.sort(key=lambda item: item[1])
            current_best_route, current_best_cost = candidate_routes[0]

            if best_route is None or current_best_cost < best_cost:
                best_route = current_best_route
                best_cost = current_best_cost

            history.append(best_cost)
            pheromone = self._evaporate_and_deposit(pheromone, candidate_routes, best_route, best_cost)

        if best_route is None:
            raise ValueError("No feasible route visits every required node and returns to the depot.")
        final_route = self._format_route(best_route, end_node=end_node)
        final_cost = self._route_cost(final_route, matrix, end_node=end_node)
        return ACOResult(route=final_route, cost=final_cost, history=history, pheromone=pheromone)

    def _construct_route(self, matrix: np.ndarray, pheromone: np.ndarray, end_node: int | None = None) -> List[int] | None:
        n = matrix.shape[0]
        current = 0
        route = [0]
        visited = {0}
        required = [node for node in range(1, n) if node != end_node]

        while len(visited) - 1 < len(required):
            choices = [idx for idx in required if idx not in visited and math.isfinite(matrix[current, idx])]
            if not choices:
                return None
            log_weights = []
            for candidate in choices:
                tau = max(float(pheromone[current, candidate]), 1e-300)
                eta = 1.0 / max(float(matrix[current, candidate]), 1e-12)
                log_weights.append(
                    self.config.alpha * math.log(tau) + self.config.beta * math.log(eta)
                )
            max_log_weight = max(log_weights)
            weights = [math.exp(value - max_log_weight) for value in log_weights]
            total_weight = sum(weights)
            threshold = self.rand.random() * total_weight
            cumulative = 0.0
            next_node = choices[-1]
            for candidate, weight in zip(choices, weights):
                cumulative += weight
                if cumulative >= threshold:
                    next_node = candidate
                    break

            route.append(next_node)
            visited.add(next_node)
            current = next_node

        terminal = end_node if end_node is not None else 0
        if not math.isfinite(matrix[current, terminal]):
            return None
        route.append(terminal)
        return route

    def _route_cost(self, route: Sequence[int], matrix: np.ndarray, end_node: int | None = None) -> float:
        if len(route) < 2:
            return float("inf")
        terminal = end_node if end_node is not None else 0
        required = set(range(1, matrix.shape[0]))
        if end_node is not None:
            required.discard(end_node)
        if route[0] != 0 or route[-1] != terminal or set(route[1:-1]) != required:
            return float("inf")
        if len(route) != len(required) + 2:
            return float("inf")

        total = 0.0
        for left, right in zip(route, route[1:]):
            if not math.isfinite(matrix[left, right]):
                return float("inf")
            total += float(matrix[left, right])
        return total

    def _evaporate_and_deposit(
        self,
        pheromone: np.ndarray,
        candidate_routes: Sequence[tuple[List[int], float]],
        best_route: Sequence[int],
        best_cost: float,
    ) -> np.ndarray:
        updated = pheromone.copy()
        updated *= 1.0 - self.config.evaporation_rate

        for i in range(updated.shape[0]):
            for j in range(updated.shape[1]):
                if i == j:
                    updated[i, j] = 0.0

        for route, cost in candidate_routes:
            deposit = max(0.0, 1.0 / (cost + 1e-9))
            for source, target in zip(route, route[1:]):
                updated[source, target] += deposit

        for source, target in zip(best_route, best_route[1:]):
            updated[source, target] += max(0.0, 1.0 / (best_cost + 1e-9))

        return updated

    def _format_route(self, route: Sequence[int], end_node: int | None = None) -> List[int]:
        if not route:
            return [0]
        formatted = list(route)
        if formatted[0] != 0:
            formatted.insert(0, 0)
        terminal = end_node if end_node is not None else 0
        if formatted[-1] != terminal:
            formatted.append(terminal)
        return formatted


def solve_tsp_aco(cost_matrix: Sequence[Sequence[float]], config: ACOConfig | None = None) -> ACOResult:
    optimizer = AntColonyOptimizer(config)
    return optimizer.optimize(cost_matrix)
