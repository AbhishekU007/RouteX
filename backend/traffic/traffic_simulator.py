from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import networkx as nx


TRAFFIC_LEVELS = {
    "normal": 1.0,
    "moderate": 0.8,
    "heavy": 0.6,
    "severe": 0.4,
}


@dataclass
class TrafficCondition:
    level: str
    multiplier: float
    speed_reduction_pct: float
    timestamp: str | None = None


class TrafficSimulator:
    """Deterministic traffic simulator for road-network edge travel times."""

    def __init__(self, seed: int | None = None):
        self.random = random.Random(seed)
        self.congestion: Dict[Tuple[int, int, int], TrafficCondition] = {}

    def apply_congestion(self, graph: nx.MultiDiGraph, edge_keys: Iterable[Tuple[int, int, int]], level: str = "moderate", speed_reduction_pct: float = 20.0) -> None:
        normalized_level = level.lower()
        if normalized_level not in TRAFFIC_LEVELS:
            raise ValueError(f"Unsupported traffic level: {level}")
        if speed_reduction_pct < 0:
            raise ValueError("Speed reduction percentage must be non-negative.")

        for edge_key in edge_keys:
            if edge_key not in graph.edges(keys=True):
                continue
            multiplier = max(0.1, TRAFFIC_LEVELS[normalized_level])
            self.congestion[edge_key] = TrafficCondition(
                level=normalized_level,
                multiplier=multiplier,
                speed_reduction_pct=speed_reduction_pct,
                timestamp=None,
            )
            u, v, key = edge_key
            edge = graph[u][v][key]
            edge["traffic_level"] = normalized_level
            edge["traffic_multiplier"] = multiplier
            edge["speed_reduction_pct"] = speed_reduction_pct

    def clear_congestion(self, graph: nx.MultiDiGraph, edge_keys: Iterable[Tuple[int, int, int]] | None = None) -> None:
        if edge_keys is None:
            keys = list(self.congestion)
        else:
            keys = list(edge_keys)
        for edge_key in keys:
            if edge_key in self.congestion:
                del self.congestion[edge_key]
            if edge_key in graph.edges(keys=True):
                u, v, key = edge_key
                edge = graph[u][v][key]
                edge.pop("traffic_level", None)
                edge.pop("traffic_multiplier", None)
                edge.pop("speed_reduction_pct", None)

    def apply_random_congestion(self, graph: nx.MultiDiGraph, level: str = "moderate", fraction: float = 0.25) -> None:
        edges = list(graph.edges(keys=True))
        if not edges or fraction <= 0:
            return
        count = max(1, int(len(edges) * max(0.0, min(1.0, fraction))))
        chosen = self.random.sample(edges, k=count)
        self.apply_congestion(graph, chosen, level=level)

    def update_edge_travel_time(self, graph: nx.MultiDiGraph, edge_key: Tuple[int, int, int]) -> None:
        if edge_key not in graph.edges(keys=True):
            return
        u, v, key = edge_key
        edge = graph[u][v][key]
        base_speed = edge.get("speed_kph") or 35.0
        traffic_multiplier = edge.get("traffic_multiplier", 1.0)
        edge["travel_time_minutes"] = max(0.1, (edge.get("length_m", 0.0) / 1000.0) / (base_speed * traffic_multiplier) * 60.0)

    def update_all_travel_times(self, graph: nx.MultiDiGraph) -> None:
        for edge_key in graph.edges(keys=True):
            self.update_edge_travel_time(graph, edge_key)


def build_traffic_profile(level: str = "moderate") -> TrafficCondition:
    normalized = level.lower()
    multiplier = TRAFFIC_LEVELS.get(normalized, TRAFFIC_LEVELS["normal"])
    return TrafficCondition(level=normalized, multiplier=multiplier, speed_reduction_pct=max(0.0, (1.0 - multiplier) * 100.0))
