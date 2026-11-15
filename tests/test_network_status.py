import networkx as nx
import pytest
from fastapi import HTTPException

from api.routes import load_network, network_status
from models.schemas import NetworkLoadRequest
from services import optimizer_service


def test_network_status_reports_the_active_graph(monkeypatch):
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0)
    graph.add_edge(2, 3, key=0)
    graph.graph.update(source="offline_fallback", fallback_reason="offline_only")
    monkeypatch.setitem(optimizer_service.STATE, "city", "Test City")
    monkeypatch.setitem(optimizer_service.STATE, "network", graph)

    assert network_status() == {
        "status": "ready",
        "city": "Test City",
        "nodes": 3,
        "edges": 2,
        "source": "offline_fallback",
        "fallback_reason": "offline_only",
        "fallback_message": None,
    }


def test_loading_unsupported_offline_city_returns_validation_error():
    with pytest.raises(HTTPException) as error:
        load_network(NetworkLoadRequest(city="Delhi, India", offline_only=True))

    assert error.value.status_code == 422
    assert "only for Agra" in error.value.detail
