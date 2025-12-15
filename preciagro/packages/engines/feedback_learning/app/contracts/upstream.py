"""Upstream contracts - Input data structures from other PreciAgro engines.

FLE receives data ONLY through these contracts from:
- UX Orchestration Engine: Explicit and implicit feedback payloads
- Diagnosis & Recommendation Engine: Recommendation IDs, confidence, metadata
- Trust & Explainability Engine: Reasoning trace IDs
- Farmer Profile Engine: Experience level, history
- Farm Inventory Engine: Action execution evidence
- Temporal Logic Engine: Outcome timing context

FLE must NOT fetch this data itself. All required references must be passed in.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict


class FeedbackType(str, Enum):
    """Types of feedback FLE can receive."""

    EXPLICIT = "explicit"  # User-provided rating/comment
    IMPLICIT = "implicit"  # Behavioral signals (clicks, time spent)
    OUTCOME = "outcome"  # Action execution results


class ExplicitFeedbackInput(BaseModel):
    """Explicit feedback from UX Orchestration Engine.

    User-provided ratings, comments, and corrections.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    feedback_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique feedback ID")

    # References to original recommendation/decision
    recommendation_id: str = Field(..., description="ID of the recommendation being rated")
    reasoning_trace_id: Optional[str] = Field(
        None, description="ID of reasoning trace from Trust Engine"
    )
    decision_id: Optional[str] = Field(None, description="ID of the decision if applicable")

    # Feedback content
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 star rating")
    feedback_category: Literal[
        "helpful",
        "not_helpful",
        "incorrect",
        "unclear",
        "missing_info",
        "too_complex",
        "too_simple",
        "other",
    ] = Field(..., description="Category of feedback")
    comment: Optional[str] = Field(None, max_length=2000, description="Free-text comment")
    suggested_correction: Optional[str] = Field(
        None, max_length=1000, description="User's suggested fix"
    )

    # User context (passed from Farmer Profile Engine)
    user_id: str = Field(..., description="User ID")
    user_role: Literal["farmer", "expert", "agronomist", "auditor"] = Field(
        default="farmer", description="User role"
    )

    # Regional scope
    region_code: str = Field(..., description="ISO country code (e.g., 'ZW', 'ZA')")

    # Metadata
    source_engine: str = Field(default="ux_orchestration", description="Source engine")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When feedback was submitted"
    )
    session_id: Optional[str] = Field(None, description="User session ID")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ImplicitFeedbackInput(BaseModel):
    """Implicit feedback from UX Orchestration Engine.

    Behavioral signals derived from user interactions.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    feedback_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique feedback ID")

    # References
    recommendation_id: str = Field(..., description="ID of the recommendation")
    reasoning_trace_id: Optional[str] = Field(None, description="Reasoning trace ID")

    # Behavioral signals
    viewed: bool = Field(default=False, description="Whether recommendation was viewed")
    view_duration_seconds: Optional[float] = Field(None, ge=0, description="Time spent viewing")
    expanded_details: bool = Field(default=False, description="Whether user expanded details")
    clicked_action: bool = Field(default=False, description="Whether user clicked action button")
    dismissed: bool = Field(default=False, description="Whether recommendation was dismissed")
    shared: bool = Field(default=False, description="Whether recommendation was shared")
    saved: bool = Field(default=False, description="Whether recommendation was saved")

    # Scroll/interaction depth
    scroll_depth: Optional[float] = Field(
        None, ge=0, le=1, description="How far user scrolled (0-1)"
    )
    interaction_count: int = Field(default=0, ge=0, description="Number of interactions")

    # User context
    user_id: str = Field(..., description="User ID")
    region_code: str = Field(..., description="Region code")

    # Metadata
    source_engine: str = Field(default="ux_orchestration", description="Source engine")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    device_type: Optional[Literal["mobile", "tablet", "desktop"]] = Field(
        None, description="Device type"
    )

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class OutcomeFeedbackInput(BaseModel):
    """Outcome feedback from Farm Inventory Engine.

    Evidence of action execution and results.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    feedback_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique feedback ID")

    # References
    recommendation_id: str = Field(..., description="ID of the recommendation")
    action_id: Optional[str] = Field(None, description="ID of the executed action")

    # Outcome data
    action_executed: bool = Field(..., description="Whether action was executed")
    execution_timestamp: Optional[datetime] = Field(None, description="When action was executed")
    outcome_observed: bool = Field(default=False, description="Whether outcome was observed")
    outcome_timestamp: Optional[datetime] = Field(None, description="When outcome was observed")

    # Result assessment
    outcome_category: Optional[
        Literal["success", "partial_success", "no_effect", "negative_effect", "unknown"]
    ] = Field(None, description="Outcome category")
    outcome_description: Optional[str] = Field(None, max_length=1000, description="Description")

    # Quantitative outcomes
    yield_change_percent: Optional[float] = Field(None, description="Yield change percentage")
    cost_savings_local: Optional[float] = Field(None, description="Cost savings in local currency")
    health_score_change: Optional[float] = Field(
        None, ge=-100, le=100, description="Crop health change"
    )

    # Evidence
    evidence_photo_refs: List[str] = Field(
        default_factory=list, description="Photo evidence references"
    )
    evidence_sensor_refs: List[str] = Field(
        default_factory=list, description="Sensor data references"
    )

    # User context
    user_id: str = Field(..., description="User ID")
    farm_id: str = Field(..., description="Farm ID")
    region_code: str = Field(..., description="Region code")

    # Metadata
    source_engine: str = Field(default="farm_inventory", description="Source engine")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Record timestamp")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RecommendationContext(BaseModel):
    """Context from Diagnosis & Recommendation Engine.

    Provides metadata about the original recommendation.
    """

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(..., description="Recommendation ID")
    recommendation_type: str = Field(..., description="Type of recommendation")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence score")

    # Decision details
    diagnosis_id: Optional[str] = Field(None, description="Related diagnosis ID")
    action_type: Optional[str] = Field(None, description="Recommended action type")
    urgency: Optional[Literal["low", "medium", "high", "critical"]] = Field(None)

    # Model info
    model_id: str = Field(..., description="Model that generated recommendation")
    model_version: str = Field(..., description="Model version")

    # Context
    crop_type: Optional[str] = Field(None, description="Crop type")
    growth_stage: Optional[str] = Field(None, description="Growth stage")
    region_code: str = Field(..., description="Region code")

    created_at: datetime = Field(..., description="When recommendation was created")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ReasoningTraceRef(BaseModel):
    """Reference to reasoning trace from Trust & Explainability Engine."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(..., description="Reasoning trace ID")
    request_id: str = Field(..., description="Original request ID")

    # Summary (not full trace, just references)
    models_used: List[str] = Field(default_factory=list, description="Model IDs used")
    evidence_count: int = Field(default=0, description="Number of evidence items")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Overall confidence")
    safety_status: Optional[Literal["passed", "warning", "blocked"]] = Field(None)

    created_at: datetime = Field(..., description="Trace creation time")


class FarmerProfileContext(BaseModel):
    """Context from Farmer Profile Engine.

    Experience level and history for weighting calculations.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., description="User ID")

    # Experience level
    experience_level: Literal["novice", "intermediate", "expert"] = Field(
        ..., description="Farmer experience level"
    )
    years_farming: Optional[int] = Field(None, ge=0, description="Years of farming experience")

    # Historical accuracy
    total_feedback_count: int = Field(default=0, ge=0, description="Total feedback given")
    accurate_feedback_count: int = Field(default=0, ge=0, description="Accurate feedback count")
    historical_accuracy: Optional[float] = Field(
        None, ge=0, le=1, description="Historical accuracy ratio"
    )

    # Engagement
    engagement_score: Optional[float] = Field(None, ge=0, le=1, description="Engagement score")
    last_active: Optional[datetime] = Field(None, description="Last active timestamp")

    # Trust indicators
    verified_identity: bool = Field(default=False, description="Identity verified")
    trusted_contributor: bool = Field(default=False, description="Marked as trusted")

    region_code: str = Field(..., description="Primary region")


class OutcomeTimingContext(BaseModel):
    """Context from Temporal Logic Engine.

    Timing information for outcome correlation.
    """

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(..., description="Recommendation ID")

    # Timing windows
    expected_outcome_days: Optional[int] = Field(None, ge=0, description="Expected days to outcome")
    actual_outcome_days: Optional[int] = Field(None, ge=0, description="Actual days to outcome")
    timing_variance_factor: Optional[float] = Field(None, description="Timing variance")

    # Environmental context
    weather_stability: Optional[float] = Field(None, ge=0, le=1, description="Weather stability")
    season_alignment: Optional[float] = Field(None, ge=0, le=1, description="Season alignment")
    environmental_factors: Dict[str, Any] = Field(default_factory=dict, description="Env factors")

    # Correlation confidence
    outcome_correlation_confidence: Optional[float] = Field(
        None, ge=0, le=1, description="Confidence that outcome relates to recommendation"
    )
