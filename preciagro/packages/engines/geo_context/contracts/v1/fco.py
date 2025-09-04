"""Field Context Object (FCO) response models."""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class LocationInfo(BaseModel):
    """Location information."""
    centroid: Dict[str, float]  # {"lat": x, "lon": y}
    admin_l0: Optional[str] = None  # Country
    admin_l1: Optional[str] = None  # State/Province
    admin_l2: Optional[str] = None  # County/District
    agro_zone: Optional[str] = None


class SoilData(BaseModel):
    """Soil information for a location."""
    texture: Optional[str] = None
    ph_range: Optional[List[float]] = None  # [min, max]
    organic_matter_pct: Optional[float] = None
    cec: Optional[float] = None  # Cation Exchange Capacity
    drainage: Optional[str] = None
    resolution: Optional[str] = None
    version: Optional[str] = None


class ClimateData(BaseModel):
    """Climate information for a location."""
    # Forecast (next 7-10 days)
    forecast_summary: Optional[Dict[str, Any]] = None

    # 30-year normals
    normals: Optional[Dict[str, float]] = None

    # Computed values
    et0_mm_day: Optional[float] = None  # Evapotranspiration (Hargreaves)
    gdd_base10_ytd: Optional[float] = None  # Growing Degree Days

    # Metadata
    version: Optional[str] = None
    last_updated: Optional[datetime] = None


class CalendarWindow(BaseModel):
    """Agricultural calendar window."""
    crop: str
    activity: str  # planting, irrigation, spraying
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    notes: Optional[str] = None


class Calendars(BaseModel):
    """Agricultural calendar information."""
    planting_windows: List[CalendarWindow] = []
    irrigation_baseline: List[CalendarWindow] = []
    no_spray_windows: List[CalendarWindow] = []


class ProvenanceEntry(BaseModel):
    """Data provenance information."""
    source: str
    version: str
    resolution: Optional[str] = None
    last_updated: Optional[datetime] = None


class FCOResponse(BaseModel):
    """Field Context Object response for MVP."""

    # Required fields
    context_hash: str = Field(..., description="Unique hash for this context")
    location: LocationInfo

    # Data sections
    soil: Optional[SoilData] = None
    climate: Optional[ClimateData] = None
    calendars: Optional[Calendars] = None

    # Metadata
    provenance: List[ProvenanceEntry] = []
    confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Overall confidence score")
    generated_at: datetime = Field(default_factory=datetime.now)

    # Performance metrics
    processing_time_ms: Optional[float] = None


# Legacy models for backward compatibility
class SpatialContext(BaseModel):
    """Spatial context information."""
    elevation: Optional[float] = None
    slope: Optional[float] = None
    aspect: Optional[float] = None
    land_use: Optional[str] = None
    administrative_region: Optional[str] = None
    nearest_weather_station: Optional[str] = None
    distance_to_water: Optional[float] = None


class CalendarEvent(BaseModel):
    """Agricultural calendar event."""
    event_type: str  # planting, harvesting, spraying, etc.
    crop_type: Optional[str] = None
    recommended_date: Optional[datetime] = None
    optimal_window_start: Optional[datetime] = None
    optimal_window_end: Optional[datetime] = None
    confidence: float = 0.0
