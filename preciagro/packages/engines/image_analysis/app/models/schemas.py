"""Pydantic schemas for the Image Analysis Engine API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator

from ..core import settings


class RequestSource(str, Enum):
    """Supported ingestion sources for an image."""

    mobile = "mobile"
    drone = "drone"
    upload = "upload"
    file_url = "file_url"


class AnalysisMetadata(BaseModel):
    """Context describing the capture event for an image."""

    field_id: Optional[str] = Field(default=None, description="Internal field identifier")
    lat: Optional[float] = Field(default=None, description="Latitude in decimal degrees")
    lon: Optional[float] = Field(default=None, description="Longitude in decimal degrees")
    captured_at: Optional[datetime] = Field(
        default=None, description="ISO timestamp representing when the photo was captured"
    )
    device: Optional[str] = Field(default=None, description="Device model or description")
    uploader_id: Optional[str] = Field(default=None, description="ID of the submitting user")
    source: Optional[RequestSource] = Field(
        default=None, description="Capture modality hint (mobile, drone, upload, etc.)"
    )
    notes: List[str] = Field(default_factory=list, description="Optional capture notes")


class ImageQualityResult(BaseModel):
    """Quality gate evaluation result."""

    passed: bool = True
    notes: List[str] = Field(default_factory=list, description="Actionable guidance when gate fails")


class DiseasePrediction(BaseModel):
    """Disease classifier output normalized to internal codes."""

    code: str = Field(..., description="Internal CIE disease code")
    label: str = Field(..., description="Human label returned to clients")
    conf: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence")


class GrowthStagePrediction(BaseModel):
    """Growth stage classifier output."""

    code: str = Field(..., description="Internal growth stage code")
    label: str = Field(..., description="Human label for the growth stage")
    conf: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence")


class CountsResult(BaseModel):
    """Optional detection counts (fruit, pests, etc.)."""

    fruit: Optional[int] = Field(default=None, ge=0)
    pest: Optional[int] = Field(default=None, ge=0)


class ResponseExplanations(BaseModel):
    """Explainability artifacts produced for the inference."""

    gradcam_url: Optional[HttpUrl] = None
    mask_url: Optional[HttpUrl] = None
    mask_binary_url: Optional[HttpUrl] = None


class ImageAnalysisResponse(BaseModel):
    """Standard JSON response contract consumed by downstream engines."""

    crop: str
    disease: DiseasePrediction
    growth_stage: GrowthStagePrediction
    health_score: float = Field(ge=0.0, le=1.0)
    lesion_area_pct: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    counts: CountsResult = Field(default_factory=CountsResult)
    quality: ImageQualityResult = Field(default_factory=ImageQualityResult)
    explanations: ResponseExplanations = Field(default_factory=ResponseExplanations)
    meta: AnalysisMetadata = Field(default_factory=AnalysisMetadata)


class ImageAnalysisRequest(BaseModel):
    """Analysis request body supporting direct upload or signed URL."""

    crop: str = Field(..., description="Normalized crop identifier (e.g., 'maize')")
    image_base64: Optional[str] = Field(
        default=None, description="Base64 encoded image when uploading directly"
    )
    image_url: Optional[HttpUrl] = Field(
        default=None, description="Signed URL to fetch the image when not uploading directly"
    )
    client_request_id: Optional[str] = Field(
        default=None, description="Idempotency key or trace identifier from the caller"
    )
    quantify_lesions: bool = Field(
        default=False,
        description="Enable lesion segmentation when supported for the crop",
    )
    count_objects: bool = Field(
        default=False,
        description="Enable fruit/pest counting when supported for the crop",
    )
    meta: AnalysisMetadata = Field(default_factory=AnalysisMetadata)

    @model_validator(mode="after")
    def ensure_image_source(self) -> "ImageAnalysisRequest":
        """Ensure at least one image source is provided."""

        if not self.image_base64 and not self.image_url:
            msg = "Either image_base64 or image_url must be provided"
            raise ValueError(msg)

        if self.image_base64:
            estimated_bytes = int(len(self.image_base64) * 3 / 4)
            if estimated_bytes > settings.MAX_BASE64_BYTES:
                msg = f"Image payload exceeds max size of {settings.MAX_BASE64_BYTES} bytes"
                raise ValueError(msg)

        return self


class BatchAnalysisRequest(BaseModel):
    """Batch wrapper for submitting multiple image analysis requests."""

    items: List[ImageAnalysisRequest] = Field(
        ..., description="List of ImageAnalysisRequest payloads."
    )

    @model_validator(mode="after")
    def enforce_batch_limit(self) -> "BatchAnalysisRequest":
        if len(self.items) > settings.MAX_BATCH_ITEMS:
            msg = f"Batch size {len(self.items)} exceeds limit of {settings.MAX_BATCH_ITEMS}"
            raise ValueError(msg)
        return self


class BatchAnalysisResponse(BaseModel):
    """Batch response containing ordered items."""

    items: List[ImageAnalysisResponse]


class HealthResponse(BaseModel):
    """Health endpoint response for probes and dashboards."""

    service: str
    status: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
