"""Request models for Geo Context Engine."""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon geometry."""
    type: str = "Polygon"
    coordinates: List[List[List[float]]]  # [[[lon, lat], ...]]


class FCORequest(BaseModel):
    """Field Context Object request for MVP."""

    # Required fields
    field: GeoJSONPolygon = Field(...,
                                  description="Field polygon in GeoJSON format")
    date: str = Field(..., description="Reference date in YYYY-MM-DD format")
    crops: List[str] = Field(default_factory=list,
                             description="List of crop types")

    # Optional fields
    units: str = Field(
        default="metric", description="Unit system (metric/imperial)")

    # Processing options
    use_cache: bool = Field(
        default=True, description="Whether to use cached results")
    forecast_days: int = Field(
        default=7, description="Number of forecast days")

    class Config:
        schema_extra = {
            "example": {
                "field": {
                    "type": "Polygon",
                    "coordinates": [[[21.0, 52.2], [21.01, 52.2], [21.01, 52.21], [21.0, 52.21], [21.0, 52.2]]]
                },
                "date": "2025-09-04",
                "crops": ["maize"],
                "units": "metric"
            }
        }


# Legacy models for backward compatibility
class LocationPoint(BaseModel):
    """Geographic point location."""
    latitude: float
    longitude: float


class LocationPolygon(BaseModel):
    """Geographic polygon area."""
    coordinates: List[List[float]]  # [[lon, lat], [lon, lat], ...]
    type: str = "polygon"
