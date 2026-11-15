import requests

import traffic.tomtom_api as tomtom_api


def test_missing_tomtom_key_returns_explicit_simulation_fallback(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "")
    monkeypatch.setattr(tomtom_api, "TOMTOM_API_KEY", "")

    result = tomtom_api.get_live_traffic("Agra")

    assert result["available"] is False
    assert result["source"] == "simulated"
    assert result["status"] == "simulation"
    assert result["data"] == []


def test_tomtom_request_failure_returns_explicit_simulation_fallback(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-key")
    monkeypatch.setattr(tomtom_api, "TOMTOM_API_KEY", "test-key")
    monkeypatch.setattr(tomtom_api.requests, "get", lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("offline")))

    result = tomtom_api.get_live_traffic("Agra")

    assert result["available"] is False
    assert result["source"] == "simulated"
    assert "request failed" in result["message"]
