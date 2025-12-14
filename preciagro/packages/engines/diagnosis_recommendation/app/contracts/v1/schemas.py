"""Input and output schemas for Diagnosis & Recommendation Engine v1."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Input Signals from Upstream Engines
# ============================================================================

class ImageAnalysisSignal(BaseModel):
    """Structured output from Image Analysis Engine."""
    
    model_config = ConfigDict(extra="allow")
    
    image_id: str = Field(..., description="Image identifier")
    detected_labels: List[str] = Field(default_factory=list, description="Detected disease/pest labels")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Confidence per label")
    visual_features: Optional[Dict[str, Any]] = Field(None, description="Visual feature vectors")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationalNLPSignal(BaseModel):
    """Structured output from Conversational/NLP Engine."""
    
    model_config = ConfigDict(extra="allow")
    
    intent: str = Field(..., description="Detected intent")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    symptoms: List[str] = Field(default_factory=list, description="Extracted symptoms")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Intent confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SensorSignal(BaseModel):
    """Structured output from sensor data."""
    
    model_config = ConfigDict(extra="allow")
    
    sensor_id: str = Field(..., description="Sensor identifier")
    sensor_type: str = Field(..., description="Sensor type (soil_moisture, temperature, etc.)")
    value: float = Field(..., description="Sensor reading")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(..., description="Reading timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GeoContextSignal(BaseModel):
    """Structured output from GeoContext Engine."""
    
    model_config = ConfigDict(extra="allow")
    
    region_code: str = Field(..., description="Region identifier")
    soil_data: Optional[Dict[str, Any]] = Field(None, description="Soil information")
    climate_data: Optional[Dict[str, Any]] = Field(None, description="Climate information")
    spatial_context: Optional[Dict[str, Any]] = Field(None, description="Spatial context")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Context confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TemporalLogicSignal(BaseModel):
    """Structured output from Temporal Logic Engine."""
    
    model_config = ConfigDict(extra="allow")
    
    current_season: Optional[str] = Field(None, description="Current season")
    growth_stage: Optional[str] = Field(None, description="Current growth stage")
    timing_windows: List[Dict[str, Any]] = Field(default_factory=list, description="Timing windows")
    calendar_events: List[Dict[str, Any]] = Field(default_factory=list, description="Calendar events")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Temporal confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CropIntelligenceSignal(BaseModel):
    """Structured output from Crop Intelligence Engine."""
    
    model_config = ConfigDict(extra="allow")
    
    crop_type: str = Field(..., description="Crop type")
    variety: Optional[str] = Field(None, description="Crop variety")
    growth_stage: Optional[str] = Field(None, description="Current growth stage")
    health_status: Optional[str] = Field(None, description="Health status")
    risks: List[Dict[str, Any]] = Field(default_factory=list, description="Identified risks")
    biological_constraints: Dict[str, Any] = Field(default_factory=dict, description="Biological constraints")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Intelligence confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class InventorySignal(BaseModel):
    """Structured output from Inventory Engine."""
    
    model_config = ConfigDict(extra="allow")
    
    available_inputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Available inputs")
    stock_levels: Dict[str, float] = Field(default_factory=dict, description="Stock levels")
    procurement_options: List[Dict[str, Any]] = Field(default_factory=list, description="Procurement options")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FarmerProfileSignal(BaseModel):
    """Structured output from Farmer Profile Engine."""
    
    model_config = ConfigDict(extra="allow")
    
    farmer_id: str = Field(..., description="Farmer identifier")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="Farmer preferences")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Farmer constraints")
    budget_class: Optional[Literal["low", "medium", "high"]] = Field(None, description="Budget class")
    experience_level: Optional[str] = Field(None, description="Experience level")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Engine Input Contract
# ============================================================================

class DREInput(BaseModel):
    """Input contract for Diagnosis & Recommendation Engine."""
    
    model_config = ConfigDict(extra="forbid")
    
    request_id: str = Field(default_factory=lambda: str(uuid4()), description="Request identifier")
    farmer_id: str = Field(..., description="Farmer identifier")
    field_id: Optional[str] = Field(None, description="Field identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Request timestamp")
    
    # Optional signals from upstream engines
    image_analysis: Optional[List[ImageAnalysisSignal]] = Field(None, description="Image analysis signals")
    conversational_nlp: Optional[ConversationalNLPSignal] = Field(None, description="NLP signals")
    sensors: Optional[List[SensorSignal]] = Field(None, description="Sensor signals")
    geo_context: Optional[GeoContextSignal] = Field(None, description="Geographic context")
    temporal_logic: Optional[TemporalLogicSignal] = Field(None, description="Temporal context")
    crop_intelligence: Optional[CropIntelligenceSignal] = Field(None, description="Crop intelligence")
    inventory: Optional[InventorySignal] = Field(None, description="Inventory status")
    farmer_profile: Optional[FarmerProfileSignal] = Field(None, description="Farmer profile")
    
    # Request metadata
    language: Literal["en", "sn", "pl"] = Field(default="en", description="Response language")
    urgency: Literal["low", "medium", "high"] = Field(default="medium", description="Request urgency")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Engine Output Contract
# ============================================================================

class SafetyWarning(BaseModel):
    """Safety warning in response."""
    
    model_config = ConfigDict(extra="forbid")
    
    level: Literal["info", "warning", "error", "critical"] = Field(..., description="Warning level")
    message: str = Field(..., description="Warning message")
    recommendation_id: Optional[str] = Field(None, description="Affected recommendation ID")
    constraint_type: Optional[str] = Field(None, description="Constraint type")


class DataRequest(BaseModel):
    """Request for additional data to improve diagnosis."""
    
    model_config = ConfigDict(extra="forbid")
    
    data_type: str = Field(..., description="Type of data needed")
    source_engine: str = Field(..., description="Source engine that can provide data")
    reason: str = Field(..., description="Reason for request")
    priority: Literal["low", "medium", "high"] = Field(default="medium", description="Request priority")


class DiagnosisResult(BaseModel):
    """Diagnosis result in response."""
    
    model_config = ConfigDict(extra="forbid")
    
    diagnosis_id: str = Field(..., description="Diagnosis identifier")
    primary_hypothesis: str = Field(..., description="Primary hypothesis name")
    primary_confidence: float = Field(..., ge=0.0, le=1.0, description="Primary hypothesis confidence")
    all_hypotheses: List[Dict[str, Any]] = Field(..., description="All ranked hypotheses")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    uncertainty_reasons: List[str] = Field(default_factory=list, description="Uncertainty reasons")


class RecommendationResult(BaseModel):
    """Recommendation result in response."""
    
    model_config = ConfigDict(extra="forbid")
    
    plan_id: str = Field(..., description="Recommendation plan identifier")
    recommendations: List[Dict[str, Any]] = Field(..., description="Ordered recommendations")
    execution_order: List[str] = Field(..., description="Recommended execution order")
    total_estimated_cost: Optional[Dict[str, Any]] = Field(None, description="Total cost estimate")
    is_validated: bool = Field(default=False, description="Whether plan passed validation")


class DREResponse(BaseModel):
    """Output contract for Diagnosis & Recommendation Engine."""
    
    model_config = ConfigDict(extra="forbid")
    
    response_id: str = Field(default_factory=lambda: str(uuid4()), description="Response identifier")
    request_id: str = Field(..., description="Original request ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Response timestamp")
    
    # Core outputs
    diagnosis: DiagnosisResult = Field(..., description="Diagnosis result")
    recommendations: RecommendationResult = Field(..., description="Recommendation plan")
    
    # Confidence and uncertainty
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    uncertainty_metrics: Dict[str, Any] = Field(default_factory=dict, description="Uncertainty metrics")
    missing_data: List[str] = Field(default_factory=list, description="Missing data sources")
    
    # Safety and constraints
    warnings: List[SafetyWarning] = Field(default_factory=list, description="Safety warnings")
    constraint_violations: List[Dict[str, Any]] = Field(default_factory=list, description="Constraint violations")
    
    # Explainability
    reasoning_trace_id: str = Field(..., description="Reasoning trace identifier")
    evidence_summary: Dict[str, Any] = Field(default_factory=dict, description="Evidence summary")
    
    # Data requests
    data_requests: List[DataRequest] = Field(default_factory=list, description="Requests for additional data")
    
    # Flags
    needs_human_review: bool = Field(default=False, description="Whether human review is required")
    escalation_reasons: List[str] = Field(default_factory=list, description="Escalation reasons")
    
    # Metadata
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

