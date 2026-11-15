from __future__ import annotations

import os
from typing import Any, Dict

import requests

from utils.config import TOMTOM_API_KEY


class TomTomTrafficError(RuntimeError):
    pass


def get_api_key() -> str:
    return os.getenv("TOMTOM_API_KEY", TOMTOM_API_KEY or "")


def get_live_traffic(city_name: str, latitude: float | None = None, longitude: float | None = None, timeout: int = 10) -> Dict[str, Any]:
    """Fetch traffic summary data from the TomTom Flow API when credentials are available."""
    api_key = get_api_key()
    if not api_key:
        return {
            "status": "simulation",
            "available": False,
            "source": "simulated",
            "message": "TOMTOM_API_KEY is not configured; live traffic is unavailable.",
            "data": [],
        }

    if latitude is None or longitude is None:
        latitude = 27.1767
        longitude = 78.0081

    endpoint = "https://api.tomtom.com/traffic/services/4/flowSegmentData/3/flow"
    params = {
        "point": f"{latitude},{longitude}",
        "unit": "KMPH",
        "openLr": "false",
        "key": api_key,
        "json": "{\"traffic\":true}",
    }
    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        segments = payload.get("flowSegmentData", [])
        if not isinstance(segments, list):
            segments = []
        return {
            "status": "live",
            "available": True,
            "source": "TomTom",
            "message": "Live traffic information loaded.",
            "data": segments,
        }
    except requests.RequestException as exc:
        return {
            "status": "simulation",
            "available": False,
            "source": "simulated",
            "message": f"Live traffic request failed: {exc}",
            "data": [],
        }
