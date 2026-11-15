from __future__ import annotations

from typing import Any, Literal

import math

from pydantic import BaseModel, Field, field_validator, model_validator


class LocationPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    label: str | None = None


class LocationRequest(BaseModel):
    city: str | None = None
    depot: LocationPoint | None = None
    stops: list[LocationPoint] = Field(default_factory=list)


class RouteConfig(BaseModel):
    num_ants: int = Field(default=20, ge=1)
    alpha: float = Field(default=1.0, ge=0, le=100)
    beta: float = Field(default=3.0, ge=0, le=100)
    evaporation_rate: float = Field(default=0.2, ge=0, lt=1)
    iterations: int = Field(default=40, ge=1)
    distance_weight: float = Field(default=0.5, ge=0)
    time_weight: float = Field(default=0.3, ge=0)
    fuel_weight: float = Field(default=0.2, ge=0)
    mileage_km_per_litre: float = Field(default=12.0, gt=0)
    traffic_factor: float = Field(default=1.0, gt=0)
    congestion_multiplier: float = Field(default=1.0, gt=0)
    random_seed: int = 42

    @field_validator("alpha", "beta", "distance_weight", "time_weight", "fuel_weight")
    @classmethod
    def finite_nonnegative(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Value must be finite.")
        return value

    @field_validator("traffic_factor", "congestion_multiplier", "mileage_km_per_litre")
    @classmethod
    def finite_positive(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Value must be finite.")
        return value

    @field_validator("evaporation_rate")
    @classmethod
    def finite_evaporation(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Value must be finite.")
        return value

    @model_validator(mode="after")
    def positive_objective_weight(self) -> "RouteConfig":
        if self.distance_weight + self.time_weight + self.fuel_weight <= 0:
            raise ValueError("At least one objective weight must be positive.")
        return self


class OptimizationRequest(BaseModel):
    city: str = "Agra, Uttar Pradesh, India"
    depot: tuple[float, float] = (27.1767, 78.0081)
    stops: list[tuple[float, float]] = Field(default_factory=list)
    config: RouteConfig = Field(default_factory=RouteConfig)

    @field_validator("depot")
    @classmethod
    def valid_depot(cls, value: tuple[float, float]) -> tuple[float, float]:
        if not all(math.isfinite(coordinate) for coordinate in value) or not (
            -90 <= value[0] <= 90 and -180 <= value[1] <= 180
        ):
            raise ValueError("Depot coordinates are invalid.")
        return value

    @field_validator("stops")
    @classmethod
    def valid_stops(cls, value: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for latitude, longitude in value:
            if not all(math.isfinite(coordinate) for coordinate in (latitude, longitude)) or not (
                -90 <= latitude <= 90 and -180 <= longitude <= 180
            ):
                raise ValueError("Delivery coordinates are invalid.")
        return value


class NetworkLoadRequest(BaseModel):
    city: str = "Agra, Uttar Pradesh, India"
    offline_only: bool = True


class TrafficSimulationRequest(BaseModel):
    level: Literal["normal", "moderate", "heavy", "severe"] = "moderate"
    fraction: float = Field(default=0.25, ge=0, le=1)
    speed_reduction_pct: float = Field(default=20.0, ge=0, le=100)
    route_index: int | None = None


class ReplanRequest(BaseModel):
    completed: list[int] = Field(default_factory=list)
    config: RouteConfig = Field(default_factory=RouteConfig)


class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: int = 0
    message: str = ""
    result: dict[str, Any] | None = None
