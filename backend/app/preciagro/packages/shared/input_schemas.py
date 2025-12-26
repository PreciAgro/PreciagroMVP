"""Centralized input validation schemas for PreciAgro.

This module provides shared, reusable Pydantic models and validators
for common input types across all engines, ensuring consistency and
early validation of user input.
"""

import re
from typing import List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from preciagro.packages.shared.exceptions import (
    InvalidGeoPolygonError,
    InvalidCoordinateError,
    InvalidDateRangeError,
    InvalidNumericThresholdError,
)


# ========== GEO VALIDATION ==========

class GeoCoordinate(BaseModel):
    """Validated geographic coordinate pair."""

    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude in decimal degrees (-90 to 90)",
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude in decimal degrees (-180 to 180)",
    )

    @field_validator("latitude", "longitude")
    @classmethod
    def validate_coordinates(cls, v: float) -> float:
        """Ensure coordinates are valid numbers."""
        if not isinstance(v, (int, float)) or not (-180 <= v <= 180):
            raise ValueError(f"Invalid coordinate value: {v}")
        return float(v)

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to (lat, lon) tuple."""
        return (self.latitude, self.longitude)


class GeoPoint(BaseModel):
    """Validated GeoJSON point geometry."""

    type: str = Field("Point", description="GeoJSON type must be Point")
    coordinates: List[float] = Field(
        ..., min_length=2, max_length=2, description="[longitude, latitude]"
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: List[float]) -> List[float]:
        """Validate coordinate array: [lon, lat]."""
        if len(v) != 2:
            raise ValueError("Coordinates must have exactly 2 elements")
        lon, lat = v
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude {lat} out of range [-90, 90]")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Longitude {lon} out of range [-180, 180]")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure type is 'Point'."""
        if v != "Point":
            raise ValueError("Type must be 'Point'")
        return v

    def to_coordinate(self) -> GeoCoordinate:
        """Convert to GeoCoordinate (swaps lon,lat to lat,lon)."""
        lon, lat = self.coordinates
        return GeoCoordinate(latitude=lat, longitude=lon)


class GeoPolygon(BaseModel):
    """Validated GeoJSON polygon geometry."""

    type: str = Field("Polygon", description="GeoJSON type must be Polygon")
    coordinates: List[List[List[float]]] = Field(
        ..., description="Array of linear rings (exterior + holes)"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure type is 'Polygon'."""
        if v != "Polygon":
            raise ValueError("Type must be 'Polygon'")
        return v

    @field_validator("coordinates")
    @classmethod
    def validate_polygon(cls, v: List[List[List[float]]]) -> List[List[List[float]]]:
        """Validate polygon structure and coordinate validity."""
        if not v:
            raise ValueError("Polygon must have at least one ring (exterior)")

        for ring_idx, ring in enumerate(v):
            if len(ring) < 4:
                raise ValueError(
                    f"Ring {ring_idx} has < 4 points; polygons must have >= 4 vertices"
                )

            # Check that ring is closed (first and last point are the same)
            if ring[0] != ring[-1]:
                raise ValueError(
                    f"Ring {ring_idx} is not closed (first != last point)")

            # Validate each coordinate pair
            for coord_idx, coord in enumerate(ring):
                if len(coord) != 2:
                    raise ValueError(
                        f"Ring {ring_idx} coordinate {coord_idx} must have 2 elements"
                    )
                lon, lat = coord
                if not (-90 <= lat <= 90):
                    raise ValueError(
                        f"Ring {ring_idx} coord {coord_idx}: invalid latitude {lat}"
                    )
                if not (-180 <= lon <= 180):
                    raise ValueError(
                        f"Ring {ring_idx} coord {coord_idx}: invalid longitude {lon}"
                    )

        return v


class GeoQuery(BaseModel):
    """Validated geographic query parameters."""

    latitude: float = Field(..., ge=-90, le=90, description="Query latitude")
    longitude: float = Field(..., ge=-180, le=180,
                             description="Query longitude")
    radius_km: Optional[float] = Field(
        None, gt=0, le=5000, description="Search radius in km (1-5000)"
    )
    polygon: Optional[GeoPolygon] = Field(
        None, description="GeoJSON polygon for query area")

    @model_validator(mode="after")
    def validate_query_params(self):
        """Ensure at least one spatial parameter is provided."""
        if self.radius_km is None and self.polygon is None:
            raise ValueError("Either radius_km or polygon must be specified")
        return self


# ========== TEMPORAL VALIDATION ==========

class DateRange(BaseModel):
    """Validated date range with sanity checks."""

    start_date: datetime = Field(..., description="Start date (inclusive)")
    end_date: datetime = Field(..., description="End date (inclusive)")
    max_days: int = Field(365, ge=1, le=3650,
                          description="Maximum allowed range in days")

    @model_validator(mode="after")
    def validate_range(self):
        """Ensure start <= end and range is within limits."""
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")

        delta = (self.end_date - self.start_date).days
        if delta > self.max_days:
            raise ValueError(
                f"Date range ({delta} days) exceeds maximum ({self.max_days} days)"
            )

        return self


class TimeRange(BaseModel):
    """Validated time range within a day."""

    hour_start: int = Field(0, ge=0, le=23, description="Start hour (0-23)")
    hour_end: int = Field(23, ge=0, le=23, description="End hour (0-23)")
    minute_start: int = Field(
        0, ge=0, le=59, description="Start minute (0-59)")
    minute_end: int = Field(59, ge=0, le=59, description="End minute (0-59)")

    @model_validator(mode="after")
    def validate_time_range(self):
        """Ensure start <= end."""
        start_mins = self.hour_start * 60 + self.minute_start
        end_mins = self.hour_end * 60 + self.minute_end

        if start_mins > end_mins:
            raise ValueError("start time must be <= end time")

        return self


class TemporalQuery(BaseModel):
    """Validated temporal query parameters."""

    start_date: Optional[datetime] = Field(
        None, description="Start date (inclusive)")
    end_date: Optional[datetime] = Field(
        None, description="End date (inclusive)")
    time_range: Optional[TimeRange] = Field(
        None, description="Time window within day")

    @model_validator(mode="after")
    def validate_temporal_query(self):
        """Validate date range if both dates provided."""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be <= end_date")

        return self


# ========== NUMERIC VALIDATION ==========

class NumericRange(BaseModel):
    """Validated numeric range with bounds checking."""

    min_value: float = Field(..., description="Minimum value (inclusive)")
    max_value: float = Field(..., description="Maximum value (inclusive)")

    @model_validator(mode="after")
    def validate_range(self):
        """Ensure min <= max."""
        if self.min_value > self.max_value:
            raise ValueError("min_value must be <= max_value")
        return self


class PercentageScore(BaseModel):
    """Validated percentage/score between 0-100."""

    value: float = Field(..., ge=0, le=100, description="Score from 0 to 100")


class RateLimit(BaseModel):
    """Validated rate limit parameters."""

    requests_per_window: int = Field(
        ..., gt=0, le=100000, description="Number of requests allowed"
    )
    window_seconds: int = Field(
        ..., gt=0, le=86400, description="Time window in seconds (1s to 24h)"
    )

    @property
    def requests_per_second(self) -> float:
        """Calculate equivalent requests per second."""
        return self.requests_per_window / self.window_seconds


# ========== VALIDATION UTILITY FUNCTIONS ==========

def validate_email(email: str) -> str:
    """Validate email format.

    Args:
        email: Email address to validate

    Returns:
        Validated email address

    Raises:
        ValueError: If email is invalid
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValueError(f"Invalid email format: {email}")
    return email.lower()


def validate_uuid4(value: str) -> str:
    """Validate UUID4 format.

    Args:
        value: UUID string to validate

    Returns:
        Validated UUID

    Raises:
        ValueError: If not valid UUID4
    """
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    if not re.match(uuid_pattern, value.lower()):
        raise ValueError(f"Invalid UUID4 format: {value}")
    return value


def validate_polygon_bounds(polygon: GeoPolygon) -> GeoPolygon:
    """Validate polygon doesn't span too wide geographically.

    Args:
        polygon: GeoPolygon to validate

    Returns:
        Same polygon if valid

    Raises:
        InvalidGeoPolygonError: If polygon is too large
    """
    exterior_ring = polygon.coordinates[0]

    lats = [coord[1] for coord in exterior_ring]
    lons = [coord[0] for coord in exterior_ring]

    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)

    # Warn if polygon is unusually large (e.g., spans a continent)
    if lat_range > 90 or lon_range > 180:
        raise InvalidGeoPolygonError(
            f"Polygon too large: {lat_range}° x {lon_range}°",
            context={"lat_range": lat_range, "lon_range": lon_range},
        )

    return polygon


# ========== PAGINATION & COMMON PARAMS ==========

class PaginationParams(BaseModel):
    """Validated pagination parameters."""

    page: int = Field(1, ge=1, le=10000, description="Page number (1-indexed)")
    page_size: int = Field(
        20, ge=1, le=500, description="Items per page (1-500)"
    )
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field(
        "asc", pattern="^(asc|desc)$", description="Sort order: asc or desc"
    )

    @property
    def skip(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size
