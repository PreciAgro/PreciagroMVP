"""LearningSignal model - Typed signal for downstream engines.

LearningSignal is the output artifact from FLE that downstream engines consume.

Key properties:
- Strict enum types for signal classification
- Scoped by target engine and region
- Versioned for orchestration compatibility
- References original recommendation
- Never propagates cross-region by default
- Consumable without interpretation
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import declarative_base

from ..contracts.downstream import SignalType

Base = declarative_base()


class LearningSignal(BaseModel):
    """Pydantic model for LearningSignal - typed signal for downstream engines."""
    
    model_config = ConfigDict(extra="forbid")
    
    # Primary identity
    signal_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique signal ID")
    version: str = Field(default="1.0", description="Signal schema version")
    
    # Signal classification
    signal_type: SignalType = Field(..., description="Type of learning signal")
    signal_strength: float = Field(..., ge=0, le=1, description="Signal strength (0-1)")
    
    # References to source feedback (multiple feedback can aggregate into one signal)
    source_feedback_ids: List[str] = Field(..., description="Source feedback IDs")
    source_weighted_ids: List[str] = Field(default_factory=list, description="Source weighted feedback IDs")
    
    # Original recommendation reference
    recommendation_id: str = Field(..., description="Original recommendation ID")
    reasoning_trace_id: Optional[str] = Field(None, description="Reasoning trace ID if available")
    
    # Target engine routing
    target_engine: Literal[
        "evaluation", "model_orchestration", "pie", "all"
    ] = Field(..., description="Target consumer engine")
    
    # Region scope
    region_scope: str = Field(..., description="Region scope of this signal")
    cross_region_propagation: bool = Field(
        default=False, description="Allow cross-region use"
    )
    
    # Model context (for Model Orchestration Engine)
    model_id: Optional[str] = Field(None, description="Model that generated recommendation")
    model_version: Optional[str] = Field(None, description="Model version")
    model_type: Optional[str] = Field(None, description="Model type (cv, tabular, llm, rule)")
    
    # Aggregation metrics
    feedback_count: int = Field(..., ge=1, description="Number of feedback items aggregated")
    average_weight: float = Field(..., ge=0, le=1, description="Average weight of aggregated feedback")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in this signal")
    
    # Timing window
    feedback_window_start: datetime = Field(..., description="Start of feedback collection window")
    feedback_window_end: datetime = Field(..., description="End of feedback collection window")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Signal creation time")
    
    # Routing status
    is_routed: bool = Field(default=False, description="Has been routed to target")
    routed_at: Optional[datetime] = Field(None, description="When routed")
    routing_stream: Optional[str] = Field(None, description="Redis stream routed to")
    
    # Audit
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Correlation ID"
    )
    audit_trace_id: Optional[str] = Field(None, description="Audit trace ID")
    
    # Additional context for consumers
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class LearningSignalDB(Base):
    """SQLAlchemy model for LearningSignal."""
    
    __tablename__ = "learning_signals"
    
    # Primary key
    signal_id = Column(String(36), primary_key=True, index=True)
    version = Column(String(10), nullable=False, default="1.0")
    
    # Signal classification
    signal_type = Column(String(30), nullable=False, index=True)
    signal_strength = Column(Float, nullable=False)
    
    # Source references
    source_feedback_ids = Column(JSONB, nullable=False)
    source_weighted_ids = Column(JSONB, nullable=False, default=list)
    
    # Recommendation reference
    recommendation_id = Column(String(36), nullable=False, index=True)
    reasoning_trace_id = Column(String(36), nullable=True)
    
    # Target routing
    target_engine = Column(String(30), nullable=False, index=True)
    
    # Region scope
    region_scope = Column(String(10), nullable=False, index=True)
    cross_region_propagation = Column(Boolean, nullable=False, default=False)
    
    # Model context
    model_id = Column(String(100), nullable=True, index=True)
    model_version = Column(String(20), nullable=True)
    model_type = Column(String(30), nullable=True)
    
    # Aggregation metrics
    feedback_count = Column(Integer, nullable=False)
    average_weight = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    
    # Timing
    feedback_window_start = Column(DateTime, nullable=False)
    feedback_window_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Routing status
    is_routed = Column(Boolean, nullable=False, default=False, index=True)
    routed_at = Column(DateTime, nullable=True)
    routing_stream = Column(String(100), nullable=True)
    
    # Audit
    correlation_id = Column(String(36), nullable=False, index=True)
    audit_trace_id = Column(String(36), nullable=True)
    
    # Context and metadata
    context = Column(JSONB, nullable=False, default=dict)
    extra_metadata = Column(JSONB, nullable=False, default=dict)
    
    # Indexes
    __table_args__ = (
        Index("ix_learning_signals_target_routed", "target_engine", "is_routed"),
        Index("ix_learning_signals_rec_type", "recommendation_id", "signal_type"),
        Index("ix_learning_signals_model_strength", "model_id", "signal_strength"),
    )
    
    def to_pydantic(self) -> LearningSignal:
        """Convert to Pydantic model."""
        return LearningSignal(
            signal_id=self.signal_id,
            version=self.version,
            signal_type=SignalType(self.signal_type),
            signal_strength=self.signal_strength,
            source_feedback_ids=self.source_feedback_ids or [],
            source_weighted_ids=self.source_weighted_ids or [],
            recommendation_id=self.recommendation_id,
            reasoning_trace_id=self.reasoning_trace_id,
            target_engine=self.target_engine,
            region_scope=self.region_scope,
            cross_region_propagation=self.cross_region_propagation,
            model_id=self.model_id,
            model_version=self.model_version,
            model_type=self.model_type,
            feedback_count=self.feedback_count,
            average_weight=self.average_weight,
            confidence_score=self.confidence_score,
            feedback_window_start=self.feedback_window_start,
            feedback_window_end=self.feedback_window_end,
            created_at=self.created_at,
            is_routed=self.is_routed,
            routed_at=self.routed_at,
            routing_stream=self.routing_stream,
            correlation_id=self.correlation_id,
            audit_trace_id=self.audit_trace_id,
            context=self.context or {},
            metadata=self.extra_metadata or {},
        )
    
    @classmethod
    def from_pydantic(cls, model: LearningSignal) -> "LearningSignalDB":
        """Create from Pydantic model."""
        return cls(
            signal_id=model.signal_id,
            version=model.version,
            signal_type=model.signal_type.value,
            signal_strength=model.signal_strength,
            source_feedback_ids=list(model.source_feedback_ids),
            source_weighted_ids=list(model.source_weighted_ids),
            recommendation_id=model.recommendation_id,
            reasoning_trace_id=model.reasoning_trace_id,
            target_engine=model.target_engine,
            region_scope=model.region_scope,
            cross_region_propagation=model.cross_region_propagation,
            model_id=model.model_id,
            model_version=model.model_version,
            model_type=model.model_type,
            feedback_count=model.feedback_count,
            average_weight=model.average_weight,
            confidence_score=model.confidence_score,
            feedback_window_start=model.feedback_window_start,
            feedback_window_end=model.feedback_window_end,
            created_at=model.created_at,
            is_routed=model.is_routed,
            routed_at=model.routed_at,
            routing_stream=model.routing_stream,
            correlation_id=model.correlation_id,
            audit_trace_id=model.audit_trace_id,
            context=dict(model.context),
            extra_metadata=dict(model.metadata),
        )
