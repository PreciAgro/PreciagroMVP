"""Core domain models for the Diagnosis & Recommendation Engine."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ObservationSource(str, Enum):
    """Source of an observation."""

    IMAGE_ANALYSIS = "image_analysis"
    CONVERSATIONAL_NLP = "conversational_nlp"
    SENSOR = "sensor"
    GEO_CONTEXT = "geo_context"
    TEMPORAL_LOGIC = "temporal_logic"
    CROP_INTELLIGENCE = "crop_intelligence"
    INVENTORY = "inventory"
    FARMER_PROFILE = "farmer_profile"
    DATA_INTEGRATION = "data_integration"


class ObservationType(str, Enum):
    """Type of observation."""

    VISUAL_SIGNAL = "visual_signal"
    SYMPTOM = "symptom"
    ENVIRONMENTAL = "environmental"
    TEMPORAL = "temporal"
    INVENTORY = "inventory"
    CONTEXTUAL = "contextual"


class Observation(BaseModel):
    """Normalized observation from upstream engines."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique observation ID")
    source: ObservationSource = Field(..., description="Source engine")
    type: ObservationType = Field(..., description="Observation type")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(), description="Observation timestamp"
    )

    # Normalized data
    signal: str = Field(
        ..., description="Normalized signal identifier (e.g., 'leaf_spot', 'yellowing')"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from source")
    value: Optional[float] = Field(None, description="Quantitative value if applicable")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")

    # Provenance
    source_engine_id: Optional[str] = Field(None, description="Source engine instance ID")
    source_request_id: Optional[str] = Field(None, description="Source request ID for traceability")


class EvidenceType(str, Enum):
    """Type of evidence."""

    DIRECT = "direct"  # Direct observation
    INFERRED = "inferred"  # Inferred from other evidence
    CONTEXTUAL = "contextual"  # Contextual support
    TEMPORAL = "temporal"  # Temporal pattern
    SPATIAL = "spatial"  # Spatial pattern


class Evidence(BaseModel):
    """Evidence linking observations to hypotheses."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique evidence ID")
    type: EvidenceType = Field(..., description="Evidence type")
    observation_ids: List[str] = Field(..., description="Linked observation IDs")
    hypothesis_id: Optional[str] = Field(None, description="Hypothesis this evidence supports")

    strength: float = Field(..., ge=0.0, le=1.0, description="Evidence strength")
    reasoning: str = Field(..., description="Human-readable reasoning for this evidence")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in evidence validity")

    # Provenance
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    source_component: str = Field(..., description="Component that created this evidence")


class EvidenceGraph(BaseModel):
    """Short-lived evidence graph linking observations to context."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), description="Graph ID")
    observations: List[Observation] = Field(..., description="All observations in graph")
    evidence: List[Evidence] = Field(..., description="All evidence edges")

    # Graph metadata
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    context_hash: Optional[str] = Field(None, description="Hash of context for caching")

    def get_observations_by_source(self, source: ObservationSource) -> List[Observation]:
        """Get observations from a specific source."""
        return [obs for obs in self.observations if obs.source == source]

    def get_evidence_for_hypothesis(self, hypothesis_id: str) -> List[Evidence]:
        """Get evidence supporting a hypothesis."""
        return [ev for ev in self.evidence if ev.hypothesis_id == hypothesis_id]


class HypothesisCategory(str, Enum):
    """Category of hypothesis."""

    DISEASE = "disease"
    PEST = "pest"
    NUTRIENT_DEFICIENCY = "nutrient_deficiency"
    WATER_STRESS = "water_stress"
    ENVIRONMENTAL_STRESS = "environmental_stress"
    MANAGEMENT_ERROR = "management_error"
    NORMAL_VARIATION = "normal_variation"
    UNKNOWN = "unknown"


class Hypothesis(BaseModel):
    """Plausible explanation for observed symptoms."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique hypothesis ID")
    category: HypothesisCategory = Field(..., description="Hypothesis category")
    name: str = Field(..., description="Human-readable hypothesis name")
    description: str = Field(..., description="Detailed description")

    # Scoring
    belief_score: float = Field(
        ..., ge=0.0, le=1.0, description="Belief score (posterior probability)"
    )
    prior_probability: float = Field(default=0.1, ge=0.0, le=1.0, description="Prior probability")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence IDs")

    # Temporal and spatial constraints
    temporal_validity: Optional[Dict[str, Any]] = Field(
        None, description="Temporal validity constraints"
    )
    spatial_validity: Optional[Dict[str, Any]] = Field(
        None, description="Spatial validity constraints"
    )

    # Metadata
    severity: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    urgency: Literal["low", "medium", "high"] = Field(default="medium")
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class Diagnosis(BaseModel):
    """Ranked diagnosis with multiple hypotheses."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), description="Diagnosis ID")
    hypotheses: List[Hypothesis] = Field(..., description="Ranked hypotheses")
    primary_hypothesis: Optional[Hypothesis] = Field(None, description="Most likely hypothesis")

    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    uncertainty_reasons: List[str] = Field(
        default_factory=list, description="Reasons for uncertainty"
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    reasoning_trace_id: Optional[str] = Field(None, description="Link to reasoning trace")


class ActionType(str, Enum):
    """Type of recommended action."""

    TREATMENT = "treatment"
    PREVENTION = "prevention"
    MONITORING = "monitoring"
    CULTURAL_PRACTICE = "cultural_practice"
    NUTRIENT_APPLICATION = "nutrient_application"
    WATER_MANAGEMENT = "water_management"
    HARVEST_ADJUSTMENT = "harvest_adjustment"
    NO_ACTION = "no_action"


class Recommendation(BaseModel):
    """Single recommended action."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), description="Recommendation ID")
    type: ActionType = Field(..., description="Action type")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed description")

    # Action details
    steps: List[str] = Field(..., description="Step-by-step instructions")
    timing: Optional[str] = Field(None, description="When to perform")
    frequency: Optional[str] = Field(None, description="How often")
    dosage: Optional[Dict[str, Any]] = Field(None, description="Dosage/quantity information")

    # Prioritization
    priority: Literal["low", "medium", "high", "urgent"] = Field(default="medium")
    impact_score: float = Field(..., ge=0.0, le=1.0, description="Expected impact score")
    cost_estimate: Optional[Dict[str, Any]] = Field(None, description="Cost estimate")

    # Constraints and safety
    constraints: List[str] = Field(default_factory=list, description="Constraints that apply")
    warnings: List[str] = Field(default_factory=list, description="Safety warnings")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites")

    # Evidence linkage
    supporting_hypothesis_ids: List[str] = Field(
        default_factory=list, description="Supporting hypotheses"
    )
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence")

    # Metadata
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in recommendation")
    alternatives: List[str] = Field(default_factory=list, description="Alternative approaches")
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class RecommendationPlan(BaseModel):
    """Multi-step recommendation plan."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), description="Plan ID")
    recommendations: List[Recommendation] = Field(..., description="Ordered recommendations")
    execution_order: List[str] = Field(
        ..., description="Recommended execution order (recommendation IDs)"
    )

    # Plan metadata
    total_estimated_cost: Optional[Dict[str, Any]] = Field(None, description="Total cost estimate")
    estimated_duration: Optional[str] = Field(None, description="Estimated time to complete")
    success_criteria: List[str] = Field(default_factory=list, description="Success criteria")

    # Validation
    is_validated: bool = Field(
        default=False, description="Whether plan passed constraint validation"
    )
    validation_errors: List[str] = Field(
        default_factory=list, description="Validation errors if any"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class ConstraintViolation(BaseModel):
    """Constraint violation record."""

    model_config = ConfigDict(extra="forbid")

    constraint_type: Literal[
        "inventory",
        "legality",
        "crop_safety",
        "environmental_risk",
        "farmer_preference",
        "temporal",
        "spatial",
    ] = Field(..., description="Type of constraint")
    severity: Literal["warning", "error", "blocking"] = Field(..., description="Violation severity")
    message: str = Field(..., description="Human-readable message")
    recommendation_id: Optional[str] = Field(None, description="Affected recommendation ID")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class UncertaintyMetric(BaseModel):
    """Uncertainty quantification."""

    model_config = ConfigDict(extra="forbid")

    overall_uncertainty: float = Field(..., ge=0.0, le=1.0, description="Overall uncertainty score")
    component_uncertainties: Dict[str, float] = Field(
        default_factory=dict, description="Per-component uncertainty"
    )
    missing_data: List[str] = Field(default_factory=list, description="Missing data sources")
    low_confidence_sources: List[str] = Field(
        default_factory=list, description="Low confidence sources"
    )
    escalation_required: bool = Field(default=False, description="Whether human review is required")
    escalation_reasons: List[str] = Field(
        default_factory=list, description="Reasons for escalation"
    )


class ReasoningTrace(BaseModel):
    """Complete reasoning trace for explainability."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), description="Trace ID")
    evidence_graph_id: str = Field(..., description="Associated evidence graph ID")
    diagnosis_id: str = Field(..., description="Associated diagnosis ID")

    # Reasoning steps
    steps: List[Dict[str, Any]] = Field(..., description="Reasoning steps")
    applied_rules: List[str] = Field(default_factory=list, description="Applied rules/patterns")
    model_inferences: List[Dict[str, Any]] = Field(
        default_factory=list, description="ML model inferences"
    )

    # Explainability
    rationale: str = Field(..., description="Human-readable rationale")
    confidence_breakdown: Dict[str, float] = Field(
        default_factory=dict, description="Confidence breakdown"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
