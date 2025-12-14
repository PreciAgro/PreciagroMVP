"""FeedbackEvent model - Immutable raw feedback record.

FeedbackEvent is the canonical source of truth for all feedback received.
It is immutable after creation and region-scoped.

Key properties:
- References recommendation_id and reasoning_trace_id
- Immutable - never updated, only created
- Region-scoped for data governance
- Engine-source tagged for lineage
"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FeedbackEvent(BaseModel):
    """Pydantic model for FeedbackEvent - immutable raw feedback record."""
    
    model_config = ConfigDict(extra="forbid", frozen=True)  # Immutable
    
    # Primary identity
    feedback_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique feedback ID")
    
    # References to recommendation and trace (REQUIRED linkage)
    recommendation_id: str = Field(..., description="ID of the recommendation this feedback is for")
    reasoning_trace_id: Optional[str] = Field(None, description="ID of reasoning trace from Trust Engine")
    decision_id: Optional[str] = Field(None, description="ID of the decision if applicable")
    
    # Feedback type and source
    feedback_type: Literal["explicit", "implicit", "outcome"] = Field(
        ..., description="Type of feedback"
    )
    source_engine: str = Field(..., description="Engine that sent this feedback")
    
    # Regional scope (for data governance)
    region_code: str = Field(..., description="ISO country code (e.g., 'ZW', 'ZA', 'KE')")
    
    # User context
    user_id: str = Field(..., description="User who provided feedback")
    user_role: Literal["farmer", "expert", "agronomist", "auditor"] = Field(
        default="farmer", description="Role of the user"
    )
    
    # Raw feedback payload (preserved exactly as received)
    raw_payload: Dict[str, Any] = Field(..., description="Original feedback payload")
    
    # Explicit feedback fields (nullable for other types)
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating if explicit")
    feedback_category: Optional[str] = Field(None, description="Feedback category")
    comment: Optional[str] = Field(None, description="User comment")
    
    # Implicit feedback fields
    view_duration_seconds: Optional[float] = Field(None, description="View duration")
    clicked_action: Optional[bool] = Field(None, description="Action button clicked")
    dismissed: Optional[bool] = Field(None, description="Was dismissed")
    
    # Outcome feedback fields
    action_executed: Optional[bool] = Field(None, description="Was action executed")
    outcome_category: Optional[str] = Field(None, description="Outcome category")
    
    # Timestamps (immutable)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When created")
    received_at: datetime = Field(default_factory=datetime.utcnow, description="When received by FLE")
    
    # Correlation and tracing
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Request correlation ID"
    )
    session_id: Optional[str] = Field(None, description="User session ID")
    
    # Initial validation status (set once at creation)
    is_valid: bool = Field(default=True, description="Initial validation passed")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors if any")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FeedbackEventDB(Base):
    """SQLAlchemy model for FeedbackEvent - immutable raw feedback record.
    
    This table is append-only. No updates or deletes are allowed.
    """
    
    __tablename__ = "feedback_events"
    
    # Primary key
    feedback_id = Column(String(36), primary_key=True, index=True)
    
    # References
    recommendation_id = Column(String(36), nullable=False, index=True)
    reasoning_trace_id = Column(String(36), nullable=True, index=True)
    decision_id = Column(String(36), nullable=True)
    
    # Type and source
    feedback_type = Column(String(20), nullable=False, index=True)
    source_engine = Column(String(50), nullable=False, index=True)
    
    # Regional scope
    region_code = Column(String(10), nullable=False, index=True)
    
    # User context
    user_id = Column(String(36), nullable=False, index=True)
    user_role = Column(String(20), nullable=False, default="farmer")
    
    # Raw payload
    raw_payload = Column(JSONB, nullable=False)
    
    # Explicit feedback
    rating = Column(Integer, nullable=True)
    feedback_category = Column(String(50), nullable=True)
    comment = Column(Text, nullable=True)
    
    # Implicit feedback
    view_duration_seconds = Column(Float, nullable=True)
    clicked_action = Column(Boolean, nullable=True)
    dismissed = Column(Boolean, nullable=True)
    
    # Outcome feedback
    action_executed = Column(Boolean, nullable=True)
    outcome_category = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Correlation
    correlation_id = Column(String(36), nullable=False, index=True)
    session_id = Column(String(36), nullable=True)
    
    # Validation
    is_valid = Column(Boolean, nullable=False, default=True)
    validation_errors = Column(JSONB, nullable=False, default=list)
    
    # Metadata (renamed to avoid SQLAlchemy reserved attribute)
    extra_metadata = Column(JSONB, nullable=False, default=dict)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_feedback_events_rec_type", "recommendation_id", "feedback_type"),
        Index("ix_feedback_events_region_time", "region_code", "created_at"),
        Index("ix_feedback_events_user_time", "user_id", "created_at"),
    )
    
    def to_pydantic(self) -> FeedbackEvent:
        """Convert to Pydantic model."""
        return FeedbackEvent(
            feedback_id=self.feedback_id,
            recommendation_id=self.recommendation_id,
            reasoning_trace_id=self.reasoning_trace_id,
            decision_id=self.decision_id,
            feedback_type=self.feedback_type,
            source_engine=self.source_engine,
            region_code=self.region_code,
            user_id=self.user_id,
            user_role=self.user_role,
            raw_payload=self.raw_payload,
            rating=self.rating,
            feedback_category=self.feedback_category,
            comment=self.comment,
            view_duration_seconds=self.view_duration_seconds,
            clicked_action=self.clicked_action,
            dismissed=self.dismissed,
            action_executed=self.action_executed,
            outcome_category=self.outcome_category,
            created_at=self.created_at,
            received_at=self.received_at,
            correlation_id=self.correlation_id,
            session_id=self.session_id,
            is_valid=self.is_valid,
            validation_errors=self.validation_errors or [],
            metadata=self.extra_metadata or {},
        )
    
    @classmethod
    def from_pydantic(cls, model: FeedbackEvent) -> "FeedbackEventDB":
        """Create from Pydantic model."""
        return cls(
            feedback_id=model.feedback_id,
            recommendation_id=model.recommendation_id,
            reasoning_trace_id=model.reasoning_trace_id,
            decision_id=model.decision_id,
            feedback_type=model.feedback_type,
            source_engine=model.source_engine,
            region_code=model.region_code,
            user_id=model.user_id,
            user_role=model.user_role,
            raw_payload=model.raw_payload,
            rating=model.rating,
            feedback_category=model.feedback_category,
            comment=model.comment,
            view_duration_seconds=model.view_duration_seconds,
            clicked_action=model.clicked_action,
            dismissed=model.dismissed,
            action_executed=model.action_executed,
            outcome_category=model.outcome_category,
            created_at=model.created_at,
            received_at=model.received_at,
            correlation_id=model.correlation_id,
            session_id=model.session_id,
            is_valid=model.is_valid,
            validation_errors=list(model.validation_errors),
            extra_metadata=dict(model.metadata),
        )
