"""AgroLLM Engine Request and Response Schemas v1."""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict


class GeoContext(BaseModel):
    """Geographic context for the request."""
    
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude")
    region_code: str = Field(..., description="Region identifier code")


class ImageFeature(BaseModel):
    """Image feature embedding and metadata."""
    
    id: str = Field(..., description="Image identifier")
    embedding: List[float] = Field(default_factory=list, description="Image embedding vector")
    labels: List[str] = Field(default_factory=list, description="Detected labels")


class SoilData(BaseModel):
    """Soil measurement data."""
    
    pH: Optional[float] = Field(None, ge=0.0, le=14.0, description="Soil pH level")
    moisture: Optional[float] = Field(None, ge=0.0, le=100.0, description="Soil moisture percentage")
    organic_matter: Optional[float] = Field(None, ge=0.0, description="Organic matter percentage")
    nitrogen: Optional[float] = Field(None, ge=0.0, description="Nitrogen level")
    phosphorus: Optional[float] = Field(None, ge=0.0, description="Phosphorus level")
    potassium: Optional[float] = Field(None, ge=0.0, description="Potassium level")


class CropData(BaseModel):
    """Crop information."""
    
    type: str = Field(..., description="Crop type (e.g., 'maize', 'rice')")
    variety: str = Field(default="local", description="Crop variety")
    growth_stage: Optional[str] = Field(None, description="Current growth stage")
    planting_date: Optional[str] = Field(None, description="Planting date (ISO8601)")


class WeatherData(BaseModel):
    """Weather conditions."""
    
    temp: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity: Optional[float] = Field(None, ge=0.0, le=100.0, description="Humidity percentage")
    rainfall: Optional[float] = Field(None, ge=0.0, description="Rainfall in mm")
    wind_speed: Optional[float] = Field(None, ge=0.0, description="Wind speed in m/s")
    forecast_days: Optional[int] = Field(None, ge=0, le=14, description="Forecast days ahead")


class SessionContext(BaseModel):
    """Previous conversation context."""
    
    message_id: Optional[str] = None
    previous_response: Optional[str] = None
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None


class ConsentData(BaseModel):
    """User consent information."""
    
    use_for_training: bool = Field(default=False, description="Consent to use data for training")


class FarmerRequest(BaseModel):
    """Farmer request schema v1 - Input to AgroLLM Engine."""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    user_id: str = Field(..., description="User identifier")
    field_id: Optional[str] = Field(None, description="Field identifier")
    geo: GeoContext = Field(..., description="Geographic context")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    language: Literal["en", "sn", "pl"] = Field(default="en", description="Language code")
    text: str = Field(..., min_length=1, description="User query text")
    images: List[str] = Field(default_factory=list, description="List of image IDs")
    image_features: List[ImageFeature] = Field(default_factory=list, description="Image features with embeddings")
    soil: Optional[SoilData] = Field(None, description="Soil measurement data")
    crop: Optional[CropData] = Field(None, description="Crop information")
    weather: Optional[WeatherData] = Field(None, description="Weather data")
    session_context: List[SessionContext] = Field(default_factory=list, description="Previous session context")
    consent: ConsentData = Field(default_factory=ConsentData, description="User consent data")
    
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO8601 timestamp format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid ISO8601 timestamp: {v}")


class RecommendedAction(BaseModel):
    """Recommended action for the farmer."""
    
    action: str = Field(..., description="Action description")
    dose: Optional[str] = Field(None, description="Dosage or quantity")
    timing: Optional[str] = Field(None, description="When to perform the action")
    cost_est: Optional[str] = Field(None, description="Estimated cost")
    priority: Literal["low", "medium", "high"] = Field(default="medium", description="Action priority")


class DiagnosisCard(BaseModel):
    """Diagnosis and recommendation card."""
    
    problem: str = Field(..., description="Identified problem")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    severity: Literal["low", "medium", "high"] = Field(..., description="Problem severity")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    recommended_actions: List[RecommendedAction] = Field(default_factory=list, description="Recommended actions")
    warnings: List[str] = Field(default_factory=list, description="Safety warnings")
    citations: List[str] = Field(default_factory=list, description="Document citations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Explainability(BaseModel):
    """Explainability information."""
    
    rationales: List[str] = Field(default_factory=list, description="Reasoning rationales")
    reasoning_graph: Optional[Dict[str, Any]] = Field(None, description="Reasoning graph structure")
    confidence_breakdown: Optional[Dict[str, float]] = Field(None, description="Confidence breakdown by component")


class ResponseFlags(BaseModel):
    """Response quality and safety flags."""
    
    low_confidence: bool = Field(default=False, description="Low confidence flag")
    needs_review: bool = Field(default=False, description="Needs human review")
    safety_warning: bool = Field(default=False, description="Safety warning present")
    constraint_violation: bool = Field(default=False, description="Constraint violation detected")


class AgroLLMResponse(BaseModel):
    """AgroLLM Engine response schema v1 - Output from AgroLLM Engine."""
    
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Response identifier")
    generated_text: str = Field(..., description="Generated response text")
    diagnosis_card: DiagnosisCard = Field(..., description="Structured diagnosis and recommendations")
    explainability: Explainability = Field(default_factory=Explainability, description="Explainability information")
    flags: ResponseFlags = Field(default_factory=ResponseFlags, description="Response flags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")








