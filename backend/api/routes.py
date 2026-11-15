from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.schemas import LocationRequest, NetworkLoadRequest, OptimizationRequest, ReplanRequest, TrafficSimulationRequest
from services.optimizer_service import (
    enqueue_optimization,
    get_analytics,
    get_current_route,
    get_job_status,
    get_locations,
    get_network_status,
    get_route_history,
    get_traffic_status,
    optimize_route,
    replan_remaining,
    reset_traffic,
    set_locations,
    set_network,
    simulate_traffic,
)

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "routex-api", "version": "0.1.0"}


@router.post("/api/network/load")
def load_network(request: NetworkLoadRequest) -> dict[str, object]:
    try:
        return set_network(request.city, request.offline_only)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/network/status")
def network_status() -> dict[str, object]:
    return get_network_status()


@router.post("/api/locations")
def save_locations(request: LocationRequest) -> dict[str, object]:
    depot = None
    if request.depot is not None:
        depot = (request.depot.latitude, request.depot.longitude)
    stops = [(stop.latitude, stop.longitude) for stop in request.stops]
    if depot is not None or stops:
        set_locations(depot=depot, stops=stops if stops else None)
    return get_locations()


@router.get("/api/locations")
def read_locations() -> dict[str, object]:
    return get_locations()


@router.post("/api/routes/optimize")
async def optimize_route_endpoint(request: OptimizationRequest) -> dict[str, str]:
    job_id = enqueue_optimization(request)
    return {"job_id": job_id, "status": "queued"}


@router.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, object]:
    return get_job_status(job_id)


@router.get("/api/routes/current")
def current_route() -> dict[str, object]:
    route = get_current_route()
    if route is None:
        return {"status": "empty", "route": [], "metrics": {}}
    return {"status": "ready", **route}


@router.get("/api/routes/history")
def route_history() -> list[dict[str, object]]:
    return get_route_history()


@router.post("/api/traffic/simulate")
def simulate_traffic_endpoint(request: TrafficSimulationRequest) -> dict[str, object]:
    return simulate_traffic(request)


@router.post("/api/traffic/reset")
def reset_traffic_endpoint() -> dict[str, object]:
    return reset_traffic()


@router.get("/api/traffic/status")
def traffic_status() -> dict[str, object]:
    return get_traffic_status()


@router.post("/api/routes/replan")
def replan_route(request: ReplanRequest) -> dict[str, object]:
    try:
        return replan_remaining(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/analytics")
def analytics() -> dict[str, object]:
    return get_analytics()
