"""Field Context Object contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FieldGeometry(BaseModel):
    """Minimal GeoJSON polygon geometry."""

    type: str = Field(default="Polygon", pattern="Polygon|polygon")
    coordinates: List[List[List[float]]]

    model_config = ConfigDict(extra="ignore")


class SoilData(BaseModel):
    """Soil information for a location."""

    model_config = ConfigDict(extra="allow")

    ph: Optional[float] = None
    ph_range: Optional[List[float]] = None
    organic_matter: Optional[float] = None
    organic_matter_pct: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    soil_type: Optional[str] = None
    drainage: Optional[str] = None
    texture: Optional[str] = None
    cec: Optional[float] = None
    resolution: Optional[str] = None
    version: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:  # pragma: no cover
        if self.organic_matter is None and self.organic_matter_pct is not None:
            self.organic_matter = self.organic_matter_pct
        if self.organic_matter_pct is None and self.organic_matter is not None:
            self.organic_matter_pct = self.organic_matter


class ClimateData(BaseModel):
    """Climate information for a location."""

    model_config = ConfigDict(extra="allow")

    temperature_avg: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    precipitation: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    growing_degree_days: Optional[float] = None
    et0_mm_day: Optional[float] = None
    forecast_summary: Optional[Dict[str, Any]] = None
    normals: Optional[Dict[str, float]] = None
    version: Optional[str] = None
    last_updated: Optional[datetime] = None


class SpatialContext(BaseModel):
    """Spatial context information."""

    model_config = ConfigDict(extra="allow")

    elevation: Optional[float] = None
    slope: Optional[float] = None
    aspect: Optional[float] = None
    land_use: Optional[str] = None
    administrative_region: Optional[str] = None
    nearest_weather_station: Optional[str] = None
    distance_to_water: Optional[float] = None
    agro_zone: Optional[str] = None
    admin_l0: Optional[str] = None
    admin_l1: Optional[str] = None
    admin_l2: Optional[str] = None


class CalendarEvent(BaseModel):
    """Agricultural calendar event."""

    model_config = ConfigDict(extra="allow")

    event_type: str
    crop_type: Optional[str] = None
    recommended_date: Optional[datetime] = None
    optimal_window_start: Optional[datetime] = None
    optimal_window_end: Optional[datetime] = None
    confidence: float = 0.0
    notes: Optional[str] = None


class FCOResponse(BaseModel):
    """Field Context Object response payload."""

    model_config = ConfigDict(extra="allow")

    context_hash: Optional[str] = None
    location: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    soil: Optional[SoilData] = None
    climate: Optional[ClimateData] = None
    spatial: Optional[SpatialContext] = None
    calendar_events: List[CalendarEvent] = Field(default_factory=list)
    planting_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    spray_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[float] = None
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    cache_hit: Optional[bool] = None

    @model_validator(mode="after")
    def _sync_confidence(self) -> "FCOResponse":
        if self.confidence_score is None:
            self.confidence_score = float(self.confidence)
        if self.confidence == 0.0 and self.confidence_score is not None:
            self.confidence = float(self.confidence_score)
        return self
