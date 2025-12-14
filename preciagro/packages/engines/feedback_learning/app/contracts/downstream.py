"""Downstream contracts - Output data structures to other PreciAgro engines.

FLE outputs ONLY to:
- Evaluation & Benchmarking Engine
- Model Orchestration Engine
- PIE Lite (Product Insights Engine)
- Human-in-the-Loop Review Tools

All outputs must be event-based, versioned, and traceable.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict


class SignalType(str, Enum):
    """Types of learning signals FLE can emit."""
    POSITIVE = "positive"           # Recommendation was helpful/correct
    NEGATIVE = "negative"           # Recommendation was unhelpful/incorrect
    UNCERTAIN = "uncertain"         # Signal quality too low to determine
    CONTRADICTION = "contradiction"  # Conflicting signals detected
    NOISE = "noise"                 # Signal classified as noise
    OUTCOME_SUCCESS = "outcome_success"      # Executed action had good outcome
    OUTCOME_FAILURE = "outcome_failure"      # Executed action had bad outcome
    OUTCOME_NEUTRAL = "outcome_neutral"      # Executed action had no effect


class FlagReason(str, Enum):
    """Reasons for flagging feedback for review."""
    LOW_WEIGHT = "low_weight"                   # Weight below threshold
    CONTRADICTION = "contradiction"              # Contradicts other feedback
    SUSPICIOUS_PATTERN = "suspicious_pattern"    # Unusual pattern detected
    REGION_MISMATCH = "region_mismatch"         # Region doesn't match
    DUPLICATE = "duplicate"                      # Potential duplicate
    EXPERT_REVIEW_REQUIRED = "expert_review"     # Needs expert review
    SAFETY_RELATED = "safety_related"            # Safety-related feedback
    HIGH_IMPACT = "high_impact"                  # High impact recommendation


class LearningSignalOutput(BaseModel):
    """Learning signal output for downstream engines.
    
    Signals are consumable without interpretation - they contain
    all necessary context for downstream processing.
    """
    model_config = ConfigDict(extra="forbid")
    
    # Identity
    signal_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique signal ID")
    version: str = Field(default="1.0", description="Signal schema version")
    
    # Signal classification
    signal_type: SignalType = Field(..., description="Type of learning signal")
    signal_strength: float = Field(..., ge=0, le=1, description="Signal strength (0-1)")
    
    # References to source
    source_feedback_ids: List[str] = Field(..., description="Source feedback IDs")
    recommendation_id: str = Field(..., description="Original recommendation ID")
    reasoning_trace_id: Optional[str] = Field(None, description="Reasoning trace ID")
    
    # Target engine and scope
    target_engine: Literal[
        "evaluation", "model_orchestration", "pie", "all"
    ] = Field(..., description="Target consumer engine")
    region_scope: str = Field(..., description="Region scope of this signal")
    cross_region_propagation: bool = Field(default=False, description="Allow cross-region use")
    
    # Model context for orchestration
    model_id: Optional[str] = Field(None, description="Model that generated recommendation")
    model_version: Optional[str] = Field(None, description="Model version")
    model_type: Optional[str] = Field(None, description="Model type")
    
    # Aggregated metrics
    feedback_count: int = Field(..., ge=1, description="Number of feedback items aggregated")
    average_weight: float = Field(..., ge=0, le=1, description="Average weight of feedback")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in signal")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Signal creation time")
    feedback_window_start: datetime = Field(..., description="Start of feedback window")
    feedback_window_end: datetime = Field(..., description="End of feedback window")
    
    # Audit trail
    correlation_id: str = Field(default_factory=lambda: str(uuid4()), description="Correlation ID")
    audit_trace_id: Optional[str] = Field(None, description="Audit trace ID for this signal")
    
    # Context for consumers
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class FlaggedFeedbackOutput(BaseModel):
    """Flagged feedback for Human-in-the-Loop review.
    
    Sent to HITL tools when feedback needs human review.
    """
    model_config = ConfigDict(extra="forbid")
    
    # Identity
    flag_id: str = Field(default_factory=lambda: str(uuid4()), description="Flag ID")
    
    # Source
    feedback_id: str = Field(..., description="Source feedback ID")
    feedback_type: str = Field(..., description="Type of feedback")
    recommendation_id: str = Field(..., description="Related recommendation ID")
    
    # Flag details
    flag_reason: FlagReason = Field(..., description="Reason for flagging")
    flag_severity: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Flag severity"
    )
    flag_description: str = Field(..., description="Description of the flag")
    
    # Computed values
    computed_weight: float = Field(..., ge=0, le=1, description="Computed feedback weight")
    weight_factors: Dict[str, float] = Field(
        default_factory=dict, description="Individual weight factors"
    )
    
    # Context for review
    feedback_summary: str = Field(..., description="Summary of the feedback")
    recommendation_summary: Optional[str] = Field(None, description="Summary of recommendation")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="User context")
    
    # Related flags
    related_flag_ids: List[str] = Field(
        default_factory=list, description="Related flag IDs"
    )
    contradiction_feedback_ids: List[str] = Field(
        default_factory=list, description="Contradicting feedback IDs"
    )
    
    # Review status
    review_status: Literal["pending", "in_review", "resolved", "dismissed"] = Field(
        default="pending", description="Review status"
    )
    assigned_reviewer: Optional[str] = Field(None, description="Assigned reviewer ID")
    review_priority: int = Field(default=5, ge=1, le=10, description="Review priority (1-10)")
    
    # Timing
    flagged_at: datetime = Field(default_factory=datetime.utcnow, description="When flagged")
    review_deadline: Optional[datetime] = Field(None, description="Review deadline")
    
    # Audit
    correlation_id: str = Field(default_factory=lambda: str(uuid4()), description="Correlation ID")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class AuditExportOutput(BaseModel):
    """Audit export for Data Governance Engine.
    
    Complete audit record for compliance and lineage tracking.
    """
    model_config = ConfigDict(extra="forbid")
    
    # Identity
    export_id: str = Field(default_factory=lambda: str(uuid4()), description="Export ID")
    export_version: str = Field(default="1.0", description="Export schema version")
    
    # Scope
    export_type: Literal["feedback", "signal", "batch"] = Field(
        ..., description="Type of export"
    )
    record_count: int = Field(..., ge=0, description="Number of records")
    
    # Time range
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")
    
    # Region
    region_code: Optional[str] = Field(None, description="Region filter")
    
    # Lineage
    source_feedback_ids: List[str] = Field(
        default_factory=list, description="Source feedback IDs"
    )
    generated_signal_ids: List[str] = Field(
        default_factory=list, description="Generated signal IDs"
    )
    
    # Processing summary
    processing_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Processing summary stats"
    )
    validation_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Validation summary stats"
    )
    
    # Data integrity
    checksum: Optional[str] = Field(None, description="Data checksum")
    signature: Optional[str] = Field(None, description="Cryptographic signature")
    
    # Export metadata
    exported_at: datetime = Field(default_factory=datetime.utcnow, description="Export timestamp")
    exported_by: str = Field(default="fle", description="Exporting engine")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class ReviewDecision(BaseModel):
    """Review decision from HITL reviewer."""
    model_config = ConfigDict(extra="forbid")
    
    flag_id: str = Field(..., description="Flag being reviewed")
    decision: Literal["accept", "reject", "modify", "escalate"] = Field(
        ..., description="Review decision"
    )
    
    # Decision details
    accepted_weight: Optional[float] = Field(None, ge=0, le=1, description="Accepted weight")
    modified_signal_type: Optional[SignalType] = Field(None, description="Modified signal type")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    escalation_reason: Optional[str] = Field(None, description="Escalation reason")
    
    # Reviewer info
    reviewer_id: str = Field(..., description="Reviewer ID")
    reviewer_notes: Optional[str] = Field(None, max_length=1000, description="Reviewer notes")
    
    # Timing
    reviewed_at: datetime = Field(default_factory=datetime.utcnow, description="Review timestamp")
