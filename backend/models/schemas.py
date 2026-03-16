import re
from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Analyze endpoint
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    image_url: Optional[str] = None
    farmer_id: str
    message: str = ""
    field_id: Optional[str] = None

    @field_validator("farmer_id")
    @classmethod
    def farmer_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("farmer_id must not be empty")
        return v


class AnalyzeResponse(BaseModel):
    insight: str
    action: str
    confidence: float
    confidence_reason: str
    urgency: Literal["low", "medium", "high", "critical"]
    follow_up: str


# ---------------------------------------------------------------------------
# Farmer endpoints
# ---------------------------------------------------------------------------

ALLOWED_CROPS = ["maize", "tobacco", "soya", "wheat", "sorghum", "cotton"]
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


class FarmerCreate(BaseModel):
    phone_number: str
    name: str
    latitude: float
    longitude: float
    language: Optional[str] = "en"

    @field_validator("phone_number")
    @classmethod
    def phone_e164(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError("phone_number must be in E.164 format, e.g. +263771234567")
        return v

    @field_validator("latitude")
    @classmethod
    def latitude_bounds(cls, v: float) -> float:
        if not (-90 <= v <= 90):
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def longitude_bounds(cls, v: float) -> float:
        if not (-180 <= v <= 180):
            raise ValueError("longitude must be between -180 and 180")
        return v


class FieldCreate(BaseModel):
    name: str
    boundary: List[List[float]]   # [[lng, lat], [lng, lat], ...]
    crop_type: str
    planting_date: str            # YYYY-MM-DD
    area_hectares: Optional[float] = None

    @field_validator("crop_type")
    @classmethod
    def crop_type_allowed(cls, v: str) -> str:
        if v.lower() not in ALLOWED_CROPS:
            raise ValueError(f"crop_type must be one of: {', '.join(ALLOWED_CROPS)}")
        return v.lower()

    @field_validator("planting_date")
    @classmethod
    def planting_date_not_future(cls, v: str) -> str:
        try:
            parsed = date.fromisoformat(v)
        except ValueError:
            raise ValueError("planting_date must be in YYYY-MM-DD format")
        if parsed > date.today():
            raise ValueError("planting_date cannot be in the future")
        return v

    @field_validator("boundary")
    @classmethod
    def boundary_min_points(cls, v: List[List[float]]) -> List[List[float]]:
        if len(v) < 3:
            raise ValueError("boundary must have at least 3 coordinate pairs")
        for point in v:
            if len(point) != 2:
                raise ValueError("each boundary point must be [longitude, latitude]")
        return v
