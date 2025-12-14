"""Core schemas for Trust & Explainability Engine v1."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

from .enums import (
    ExplanationLevel,
    UncertaintyType,
    SafetyStatus,
    EvidenceType,
    ExplanationStrategy,
    ViolationSeverity,
)


# ============================================================================
# Evidence & Provenance
# ============================================================================

class EvidenceItem(BaseModel):
    """Individual evidence piece with source and provenance.
    
    Evidence items store references, not copies, to maintain data lineage.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Evidence ID")
    evidence_type: EvidenceType = Field(..., description="Type of evidence")
    source_engine: str = Field(..., description="Engine that produced this evidence")
    source_id: str = Field(..., description="ID reference in source engine")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When evidence was collected")
    
    # Content reference (not the data itself to avoid duplication)
    content_ref: Optional[str] = Field(None, description="Reference URI to actual content")
    content_hash: Optional[str] = Field(None, description="SHA-256 hash of content for verification")
    
    # Summary for quick access
    summary: str = Field(default="", description="Brief summary of evidence")
    
    # Quality indicators
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidence quality confidence")
    freshness_hours: Optional[float] = Field(None, description="Hours since data collection")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ModelInfo(BaseModel):
    """Information about a model involved in the decision."""
    
    model_config = ConfigDict(extra="forbid")
    
    model_id: str = Field(..., description="Model identifier")
    model_name: str = Field(..., description="Human-readable model name")
    model_version: str = Field(..., description="Model version")
    model_type: str = Field(..., description="Model type (cv, tabular, llm, rule)")
    
    # Performance metrics at time of inference
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model confidence")
    latency_ms: Optional[float] = Field(None, description="Inference latency in ms")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Explanations
# ============================================================================

class ExplanationArtifact(BaseModel):
    """Generated explanation artifact.
    
    Can be text, image (saliency map), structured data, or visualization.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Artifact ID")
    strategy: ExplanationStrategy = Field(..., description="Strategy used to generate")
    level: ExplanationLevel = Field(..., description="Target audience level")
    
    # Content
    content_type: Literal["text", "image", "structured", "html"] = Field(
        ..., description="Type of content"
    )
    content: str = Field(..., description="Explanation content (text or base64 for images)")
    
    # For structured explanations
    structured_data: Optional[Dict[str, Any]] = Field(
        None, description="Structured explanation data (feature importance, etc.)"
    )
    
    # Evidence linking - every explanation cites evidence
    cited_evidence_ids: List[str] = Field(
        default_factory=list, description="IDs of evidence cited in this explanation"
    )
    
    # Quality metrics
    relevance_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Relevance to the decision"
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Confidence & Uncertainty
# ============================================================================

class ConfidenceMetrics(BaseModel):
    """Calibrated confidence with uncertainty quantification."""
    
    model_config = ConfigDict(extra="forbid")
    
    # Overall confidence
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall calibrated confidence")
    
    # Uncertainty breakdown
    uncertainty_type: UncertaintyType = Field(..., description="Primary uncertainty type")
    epistemic_uncertainty: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Epistemic uncertainty (reducible)"
    )
    aleatoric_uncertainty: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Aleatoric uncertainty (irreducible)"
    )
    
    # Ensemble metrics (if applicable)
    ensemble_agreement: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Agreement across ensemble members"
    )
    num_ensemble_members: Optional[int] = Field(None, description="Number of ensemble members")
    
    # Confidence breakdown by component
    component_confidences: Dict[str, float] = Field(
        default_factory=dict, description="Confidence per component/model"
    )
    
    # Calibration quality
    calibration_method: Optional[str] = Field(None, description="Calibration method used")
    calibration_error: Optional[float] = Field(
        None, ge=0.0, description="Expected calibration error"
    )
    
    # Thresholds
    meets_high_threshold: bool = Field(default=False, description="Meets high confidence threshold")
    meets_action_threshold: bool = Field(default=True, description="Meets threshold for action")


# ============================================================================
# Safety & Compliance
# ============================================================================

class SafetyViolation(BaseModel):
    """Safety or compliance violation record."""
    
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Violation ID")
    violation_type: str = Field(..., description="Type of violation")
    severity: ViolationSeverity = Field(..., description="Violation severity")
    
    # Details
    message: str = Field(..., description="Human-readable violation message")
    field: Optional[str] = Field(None, description="Affected field/parameter")
    
    # Remediation
    suggested_fix: Optional[str] = Field(None, description="Suggested remediation")
    can_override: bool = Field(default=False, description="Whether violation can be overridden")
    
    # Context
    rule_id: Optional[str] = Field(None, description="ID of rule that triggered violation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SafetyCheckResult(BaseModel):
    """Result of safety gate validation."""
    
    model_config = ConfigDict(extra="forbid")
    
    status: SafetyStatus = Field(..., description="Overall safety status")
    violations: List[SafetyViolation] = Field(
        default_factory=list, description="List of violations"
    )
    
    # Summary
    blocking_count: int = Field(default=0, description="Number of blocking violations")
    warning_count: int = Field(default=0, description="Number of warnings")
    info_count: int = Field(default=0, description="Number of info violations")
    
    # Checks performed
    compliance_checked: bool = Field(default=False, description="Compliance rules checked")
    safety_limits_checked: bool = Field(default=False, description="Safety limits checked")
    inventory_checked: bool = Field(default=False, description="Inventory availability checked")
    
    # Context
    region_code: Optional[str] = Field(None, description="Region for compliance check")
    checked_at: datetime = Field(
        default_factory=datetime.utcnow, description="When check was performed"
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Reasoning Trace (Canonical Object)
# ============================================================================

class ReasoningTrace(BaseModel):
    """Canonical reasoning trace - single source of truth for trust and audits.
    
    This object is immutable after creation and contains all information
    needed to understand why a decision was made.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    # Identity
    trace_id: str = Field(default_factory=lambda: str(uuid4()), description="Trace ID")
    request_id: str = Field(..., description="Original request ID")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Trace creation timestamp"
    )
    
    # Input references
    input_refs: Dict[str, str] = Field(
        default_factory=dict, description="References to input data"
    )
    
    # Models involved
    models: List[ModelInfo] = Field(
        default_factory=list, description="Models involved in decision"
    )
    
    # Evidence used
    evidence: List[EvidenceItem] = Field(
        default_factory=list, description="Evidence used in decision"
    )
    
    # Explanations generated
    explanations: List[ExplanationArtifact] = Field(
        default_factory=list, description="Generated explanations"
    )
    
    # Confidence metrics
    confidence: Optional[ConfidenceMetrics] = Field(
        None, description="Confidence and uncertainty metrics"
    )
    
    # Safety checks
    safety_check: Optional[SafetyCheckResult] = Field(
        None, description="Safety gate result"
    )
    
    # Decision outcome
    decision_id: Optional[str] = Field(None, description="ID of the decision/recommendation")
    decision_type: Optional[str] = Field(None, description="Type of decision")
    decision_summary: Optional[str] = Field(None, description="Brief decision summary")
    
    # Provenance
    engine_version: str = Field(default="1.0.0", description="TEE version")
    
    # Audit hooks
    signature: Optional[str] = Field(
        None, description="Cryptographic signature (for audit compliance)"
    )
    signature_algorithm: Optional[str] = Field(None, description="Signature algorithm used")
    
    # Feedback
    feedback_enabled: bool = Field(default=True, description="Whether feedback is enabled")
    feedback_url: Optional[str] = Field(None, description="URL for submitting feedback")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# API Request/Response Contracts
# ============================================================================

class ExplanationRequest(BaseModel):
    """Input contract for explanation requests."""
    
    model_config = ConfigDict(extra="forbid")
    
    request_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Request ID"
    )
    
    # What to explain
    decision_id: Optional[str] = Field(None, description="ID of decision to explain")
    model_type: str = Field(..., description="Type of model (cv, tabular, llm, rule)")
    model_id: str = Field(..., description="Model identifier")
    model_outputs: Dict[str, Any] = Field(..., description="Model outputs to explain")
    
    # Context
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Context (crop, region, farmer_id, etc.)"
    )
    
    # Evidence (optional - will be collected if not provided)
    evidence: Optional[List[Dict[str, Any]]] = Field(
        None, description="Pre-collected evidence"
    )
    
    # Configuration
    levels: List[ExplanationLevel] = Field(
        default=[ExplanationLevel.FARMER], description="Explanation levels to generate"
    )
    include_safety_check: bool = Field(
        default=True, description="Whether to run safety gate"
    )
    include_confidence: bool = Field(
        default=True, description="Whether to compute confidence metrics"
    )
    
    # Language
    language: Literal["en", "sn", "pl"] = Field(
        default="en", description="Output language"
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ExplanationResponse(BaseModel):
    """Output contract for explanation responses."""
    
    model_config = ConfigDict(extra="forbid")
    
    request_id: str = Field(..., description="Original request ID")
    trace_id: str = Field(..., description="Reasoning trace ID")
    
    # Tiered explanations
    farmer_explanation: Optional[str] = Field(
        None, description="One-line farmer-friendly explanation"
    )
    expert_explanation: Optional[str] = Field(
        None, description="Detailed expert explanation"
    )
    auditor_trace: Optional[ReasoningTrace] = Field(
        None, description="Full reasoning trace for auditors"
    )
    
    # Visual artifacts
    saliency_thumbnail: Optional[str] = Field(
        None, description="Base64 saliency thumbnail (for CV)"
    )
    feature_importance: Optional[Dict[str, float]] = Field(
        None, description="Feature importance scores (for tabular)"
    )
    
    # Confidence summary
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Overall confidence"
    )
    confidence_level: Optional[Literal["high", "medium", "low"]] = Field(
        None, description="Confidence level category"
    )
    
    # Safety status
    safety_status: SafetyStatus = Field(
        default=SafetyStatus.PASSED, description="Safety gate status"
    )
    safety_warnings: List[str] = Field(
        default_factory=list, description="Safety warnings"
    )
    
    # Feedback
    feedback_url: Optional[str] = Field(None, description="URL for feedback submission")
    
    # Performance
    processing_time_ms: Optional[float] = Field(
        None, description="Processing time in milliseconds"
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FeedbackPayload(BaseModel):
    """Feedback submission payload."""
    
    model_config = ConfigDict(extra="forbid")
    
    trace_id: str = Field(..., description="Reasoning trace ID")
    feedback_type: Literal[
        "helpful", "not_helpful", "incorrect", "unclear", "missing_info", "other"
    ] = Field(..., description="Type of feedback")
    
    # Rating
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating")
    
    # Details
    comment: Optional[str] = Field(None, max_length=1000, description="Free-text comment")
    
    # Corrections
    suggested_correction: Optional[str] = Field(
        None, description="Suggested correction if incorrect"
    )
    
    # User context
    user_id: Optional[str] = Field(None, description="User ID")
    user_role: Optional[Literal["farmer", "expert", "auditor"]] = Field(
        None, description="User role"
    )
    
    submitted_at: datetime = Field(
        default_factory=datetime.utcnow, description="Submission timestamp"
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
