"""Request models for Geo Context Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .fco import FieldGeometry


class LocationPoint(BaseModel):
    """Geographic point location."""

    latitude: float
    longitude: float


class LocationPolygon(BaseModel):
    """Geographic polygon area."""

    coordinates: List[List[float]]  # [[lon, lat], ...]
    type: str = Field(default="polygon", pattern="polygon|Polygon")

    model_config = ConfigDict(extra="ignore")


class FCORequest(BaseModel):
    """Field Context Object request payload."""

    field: Optional[FieldGeometry] = None
    point: Optional[LocationPoint] = None
    polygon: Optional[LocationPolygon] = None
    reference_date: Optional[datetime] = Field(
        default=None,
        alias="date",
        description="Reference date for the field context calculation",
    )
    forecast_days: int = Field(default=7, ge=0, le=30)
    include_soil: bool = True
    include_climate: bool = True
    include_spatial: bool = True
    include_calendar: bool = False
    include_rules: bool = True
    crop_types: List[str] = Field(default_factory=list)
    use_cache: bool = True
    units: str = Field(default="metric", pattern="metric|imperial")
    metadata: Dict[str, str] = Field(default_factory=dict)
    timezone: str = Field(default="UTC")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )

    @model_validator(mode="after")
    def _validate_location(cls, values: "FCORequest") -> "FCORequest":
        """Ensure a point or polygon is provided."""
        if values.field is not None and values.polygon is None:
            ring = values.field.coordinates[0] if values.field.coordinates else []
            values.polygon = LocationPolygon(coordinates=[[lon, lat] for lon, lat in ring])

        return values

    def get_location(self) -> Dict[str, float]:
        """Return canonical latitude/longitude pair."""
        if self.point:
            return {"lat": self.point.latitude, "lon": self.point.longitude}

        # Fall back to polygon centroid
        polygon = self.polygon
        if polygon is None and self.field is not None:
            polygon = LocationPolygon(
                coordinates=[[lon, lat] for lon, lat in self.field.coordinates[0]]
            )
        if polygon is None:
            raise ValueError("Either point or polygon must be provided")

        coords = polygon.coordinates
        if not coords:
            raise ValueError("Either point or polygon must be provided")

        lats = [coord[1] for coord in coords]
        lons = [coord[0] for coord in coords]
        return {
            "lat": sum(lats) / len(lats),
            "lon": sum(lons) / len(lons),
        }

    def get_reference_date(self) -> datetime:
        """Return a timezone-aware reference date."""
        if self.reference_date:
            dt = self.reference_date
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc)
