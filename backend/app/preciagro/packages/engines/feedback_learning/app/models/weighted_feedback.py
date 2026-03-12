"""WeightedFeedback model - Derived artifact from feedback processing.

WeightedFeedback is computed from FeedbackEvent using the weighting formula:
Weight = base_confidence × farmer_experience_factor × historical_accuracy_factor
         × model_confidence_factor × environmental_stability_factor

Key properties:
- Links to source FeedbackEvent (never overwrites it)
- Contains computed weight and quality flags
- Derived artifact - can be recomputed if formula changes
- Trust score for downstream consumers
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, DateTime, Float, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class WeightedFeedback(BaseModel):
    """Pydantic model for WeightedFeedback - derived weighted artifact."""

    model_config = ConfigDict(extra="forbid")

    # Primary identity
    weighted_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Weighted feedback ID"
    )

    # Link to source (never overwritten)
    source_feedback_id: str = Field(..., description="Source FeedbackEvent ID")
    recommendation_id: str = Field(..., description="Recommendation ID")

    # Computed weight and factors
    final_weight: float = Field(..., ge=0, le=1, description="Final computed weight")
    base_confidence: float = Field(..., ge=0, le=1, description="Base confidence value")
    farmer_experience_factor: float = Field(..., ge=0, le=1, description="Farmer experience factor")
    historical_accuracy_factor: float = Field(
        ..., ge=0, le=1, description="Historical accuracy factor"
    )
    model_confidence_factor: float = Field(..., ge=0, le=1, description="Model confidence factor")
    environmental_stability_factor: float = Field(
        ..., ge=0, le=1, description="Environmental stability"
    )

    # Trust and quality
    trust_score: float = Field(..., ge=0, le=1, description="Trust score for this feedback")
    quality_score: float = Field(..., ge=0, le=1, description="Quality score")

    # Flags
    is_flagged: bool = Field(default=False, description="Flagged for review")
    flag_reasons: List[str] = Field(default_factory=list, description="List of flag reasons")

    is_noise: bool = Field(default=False, description="Classified as noise")
    is_duplicate: bool = Field(default=False, description="Detected as duplicate")
    is_contradiction: bool = Field(default=False, description="Contradicts other feedback")

    # Duplicate detection
    duplicate_of_id: Optional[str] = Field(None, description="ID of original if duplicate")
    contradiction_with_ids: List[str] = Field(
        default_factory=list, description="IDs of contradicting feedback"
    )

    # Region scope
    region_code: str = Field(..., description="Region code")

    # Processing info
    weighting_version: str = Field(default="1.0", description="Weighting formula version")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="When processed")

    # Audit reference
    audit_trace_id: Optional[str] = Field(None, description="Audit trace ID")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WeightedFeedbackDB(Base):
    """SQLAlchemy model for WeightedFeedback - derived weighted artifact."""

    __tablename__ = "weighted_feedback"

    # Primary key
    weighted_id = Column(String(36), primary_key=True, index=True)

    # Link to source
    source_feedback_id = Column(
        String(36),
        ForeignKey("feedback_events.feedback_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    recommendation_id = Column(String(36), nullable=False, index=True)

    # Computed weight
    final_weight = Column(Float, nullable=False)
    base_confidence = Column(Float, nullable=False)
    farmer_experience_factor = Column(Float, nullable=False)
    historical_accuracy_factor = Column(Float, nullable=False)
    model_confidence_factor = Column(Float, nullable=False)
    environmental_stability_factor = Column(Float, nullable=False)

    # Trust and quality
    trust_score = Column(Float, nullable=False)
    quality_score = Column(Float, nullable=False)

    # Flags
    is_flagged = Column(Boolean, nullable=False, default=False, index=True)
    flag_reasons = Column(JSONB, nullable=False, default=list)

    is_noise = Column(Boolean, nullable=False, default=False)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    is_contradiction = Column(Boolean, nullable=False, default=False)

    # Duplicate detection
    duplicate_of_id = Column(String(36), nullable=True)
    contradiction_with_ids = Column(JSONB, nullable=False, default=list)

    # Region
    region_code = Column(String(10), nullable=False, index=True)

    # Processing info
    weighting_version = Column(String(10), nullable=False, default="1.0")
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Audit
    audit_trace_id = Column(String(36), nullable=True, index=True)

    # Metadata
    extra_metadata = Column(JSONB, nullable=False, default=dict)

    # Indexes
    __table_args__ = (
        Index("ix_weighted_feedback_rec_weight", "recommendation_id", "final_weight"),
        Index("ix_weighted_feedback_region_flagged", "region_code", "is_flagged"),
    )

    def to_pydantic(self) -> WeightedFeedback:
        """Convert to Pydantic model."""
        return WeightedFeedback(
            weighted_id=self.weighted_id,
            source_feedback_id=self.source_feedback_id,
            recommendation_id=self.recommendation_id,
            final_weight=self.final_weight,
            base_confidence=self.base_confidence,
            farmer_experience_factor=self.farmer_experience_factor,
            historical_accuracy_factor=self.historical_accuracy_factor,
            model_confidence_factor=self.model_confidence_factor,
            environmental_stability_factor=self.environmental_stability_factor,
            trust_score=self.trust_score,
            quality_score=self.quality_score,
            is_flagged=self.is_flagged,
            flag_reasons=self.flag_reasons or [],
            is_noise=self.is_noise,
            is_duplicate=self.is_duplicate,
            is_contradiction=self.is_contradiction,
            duplicate_of_id=self.duplicate_of_id,
            contradiction_with_ids=self.contradiction_with_ids or [],
            region_code=self.region_code,
            weighting_version=self.weighting_version,
            processed_at=self.processed_at,
            audit_trace_id=self.audit_trace_id,
            metadata=self.extra_metadata or {},
        )

    @classmethod
    def from_pydantic(cls, model: WeightedFeedback) -> "WeightedFeedbackDB":
        """Create from Pydantic model."""
        return cls(
            weighted_id=model.weighted_id,
            source_feedback_id=model.source_feedback_id,
            recommendation_id=model.recommendation_id,
            final_weight=model.final_weight,
            base_confidence=model.base_confidence,
            farmer_experience_factor=model.farmer_experience_factor,
            historical_accuracy_factor=model.historical_accuracy_factor,
            model_confidence_factor=model.model_confidence_factor,
            environmental_stability_factor=model.environmental_stability_factor,
            trust_score=model.trust_score,
            quality_score=model.quality_score,
            is_flagged=model.is_flagged,
            flag_reasons=list(model.flag_reasons),
            is_noise=model.is_noise,
            is_duplicate=model.is_duplicate,
            is_contradiction=model.is_contradiction,
            duplicate_of_id=model.duplicate_of_id,
            contradiction_with_ids=list(model.contradiction_with_ids),
            region_code=model.region_code,
            weighting_version=model.weighting_version,
            processed_at=model.processed_at,
            audit_trace_id=model.audit_trace_id,
            extra_metadata=dict(model.metadata),
        )
