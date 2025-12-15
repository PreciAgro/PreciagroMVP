"""FeedbackAuditTrace model - Step-by-step transformation log.

AuditTrace provides complete transparency into how feedback was processed.
Required for Trust Engine audits and data governance compliance.

Key properties:
- Step-by-step processing log
- Immutable, append-only
- Tracks every transformation
- Links all artifacts together
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, DateTime, Text, Integer, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AuditStep(BaseModel):
    """Individual step in the audit trace."""

    model_config = ConfigDict(extra="forbid", frozen=True)  # Immutable

    step_id: str = Field(default_factory=lambda: str(uuid4()), description="Step ID")
    step_number: int = Field(..., ge=1, description="Sequential step number")

    # Step type
    step_type: Literal[
        "received",
        "validated",
        "weighted",
        "flagged",
        "signal_generated",
        "routed",
        "reviewed",
        "error",
    ] = Field(..., description="Type of processing step")

    # Step details
    description: str = Field(..., description="Human-readable step description")

    # Input/output references
    input_artifact_id: Optional[str] = Field(None, description="Input artifact ID")
    input_artifact_type: Optional[str] = Field(None, description="Input artifact type")
    output_artifact_id: Optional[str] = Field(None, description="Output artifact ID")
    output_artifact_type: Optional[str] = Field(None, description="Output artifact type")

    # Transformation details
    transformation_applied: Optional[str] = Field(None, description="Transformation name")
    transformation_params: Dict[str, Any] = Field(
        default_factory=dict, description="Transformation parameters"
    )

    # Values before and after
    values_before: Dict[str, Any] = Field(default_factory=dict, description="Values before step")
    values_after: Dict[str, Any] = Field(default_factory=dict, description="Values after step")

    # Result
    success: bool = Field(default=True, description="Step succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Step start time")
    completed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Step completion time"
    )
    duration_ms: Optional[float] = Field(None, description="Step duration in milliseconds")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FeedbackAuditTrace(BaseModel):
    """Complete audit trace for feedback processing."""

    model_config = ConfigDict(extra="forbid")

    # Primary identity
    trace_id: str = Field(default_factory=lambda: str(uuid4()), description="Audit trace ID")

    # Source reference
    source_feedback_id: str = Field(..., description="Source feedback event ID")
    recommendation_id: str = Field(..., description="Recommendation ID")

    # Processing steps (ordered list)
    steps: List[AuditStep] = Field(default_factory=list, description="Processing steps")

    # Final artifacts produced
    weighted_feedback_id: Optional[str] = Field(None, description="Weighted feedback ID if created")
    learning_signal_ids: List[str] = Field(
        default_factory=list, description="Learning signal IDs if created"
    )
    flag_id: Optional[str] = Field(None, description="Flag ID if flagged")

    # Overall status
    status: Literal["processing", "completed", "error", "flagged"] = Field(
        default="processing", description="Overall processing status"
    )
    error_message: Optional[str] = Field(None, description="Error if failed")

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Processing start")
    completed_at: Optional[datetime] = Field(None, description="Processing completion")
    total_duration_ms: Optional[float] = Field(None, description="Total duration in ms")

    # Correlation
    correlation_id: str = Field(default_factory=lambda: str(uuid4()), description="Correlation ID")

    # Signature for integrity (optional, for compliance)
    signature: Optional[str] = Field(None, description="Cryptographic signature")
    signature_algorithm: Optional[str] = Field(None, description="Signature algorithm")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def add_step(
        self, step_type: str, description: str, success: bool = True, **kwargs
    ) -> AuditStep:
        """Add a new step to the trace."""
        step = AuditStep(
            step_number=len(self.steps) + 1,
            step_type=step_type,
            description=description,
            success=success,
            **kwargs,
        )
        self.steps.append(step)
        return step


class AuditStepDB(Base):
    """SQLAlchemy model for individual audit steps."""

    __tablename__ = "audit_steps"

    step_id = Column(String(36), primary_key=True, index=True)
    trace_id = Column(
        String(36),
        ForeignKey("feedback_audit_traces.trace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number = Column(Integer, nullable=False)

    step_type = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)

    input_artifact_id = Column(String(36), nullable=True)
    input_artifact_type = Column(String(30), nullable=True)
    output_artifact_id = Column(String(36), nullable=True)
    output_artifact_type = Column(String(30), nullable=True)

    transformation_applied = Column(String(100), nullable=True)
    transformation_params = Column(JSONB, nullable=False, default=dict)

    values_before = Column(JSONB, nullable=False, default=dict)
    values_after = Column(JSONB, nullable=False, default=dict)

    success = Column(Integer, nullable=False, default=True)  # Boolean as int for SQLite compat
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    duration_ms = Column(Integer, nullable=True)

    extra_metadata = Column(JSONB, nullable=False, default=dict)

    __table_args__ = (Index("ix_audit_steps_trace_number", "trace_id", "step_number"),)


class FeedbackAuditTraceDB(Base):
    """SQLAlchemy model for FeedbackAuditTrace."""

    __tablename__ = "feedback_audit_traces"

    trace_id = Column(String(36), primary_key=True, index=True)

    source_feedback_id = Column(String(36), nullable=False, index=True)
    recommendation_id = Column(String(36), nullable=False, index=True)

    weighted_feedback_id = Column(String(36), nullable=True, index=True)
    learning_signal_ids = Column(JSONB, nullable=False, default=list)
    flag_id = Column(String(36), nullable=True)

    status = Column(String(20), nullable=False, default="processing", index=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    total_duration_ms = Column(Integer, nullable=True)

    correlation_id = Column(String(36), nullable=False, index=True)

    signature = Column(Text, nullable=True)
    signature_algorithm = Column(String(20), nullable=True)

    extra_metadata = Column(JSONB, nullable=False, default=dict)

    __table_args__ = (Index("ix_audit_traces_rec_status", "recommendation_id", "status"),)

    def to_pydantic(self, steps: List[AuditStep] = None) -> FeedbackAuditTrace:
        """Convert to Pydantic model."""
        return FeedbackAuditTrace(
            trace_id=self.trace_id,
            source_feedback_id=self.source_feedback_id,
            recommendation_id=self.recommendation_id,
            steps=steps or [],
            weighted_feedback_id=self.weighted_feedback_id,
            learning_signal_ids=self.learning_signal_ids or [],
            flag_id=self.flag_id,
            status=self.status,
            error_message=self.error_message,
            started_at=self.started_at,
            completed_at=self.completed_at,
            total_duration_ms=self.total_duration_ms,
            correlation_id=self.correlation_id,
            signature=self.signature,
            signature_algorithm=self.signature_algorithm,
            metadata=self.extra_metadata or {},
        )

    @classmethod
    def from_pydantic(cls, model: FeedbackAuditTrace) -> "FeedbackAuditTraceDB":
        """Create from Pydantic model (steps stored separately)."""
        return cls(
            trace_id=model.trace_id,
            source_feedback_id=model.source_feedback_id,
            recommendation_id=model.recommendation_id,
            weighted_feedback_id=model.weighted_feedback_id,
            learning_signal_ids=list(model.learning_signal_ids),
            flag_id=model.flag_id,
            status=model.status,
            error_message=model.error_message,
            started_at=model.started_at,
            completed_at=model.completed_at,
            total_duration_ms=model.total_duration_ms,
            correlation_id=model.correlation_id,
            signature=model.signature,
            signature_algorithm=model.signature_algorithm,
            extra_metadata=dict(model.metadata),
        )
