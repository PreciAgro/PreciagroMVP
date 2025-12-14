"""Schema Tests for Feedback & Learning Engine.

Tests the Pydantic models for:
- Upstream contracts
- Downstream contracts
- Data models
"""

import pytest
from datetime import datetime
from uuid import uuid4

from preciagro.packages.engines.feedback_learning.app.contracts.upstream import (
    ExplicitFeedbackInput,
    ImplicitFeedbackInput,
    OutcomeFeedbackInput,
    FarmerProfileContext,
    RecommendationContext,
    FeedbackType,
)
from preciagro.packages.engines.feedback_learning.app.contracts.downstream import (
    LearningSignalOutput,
    FlaggedFeedbackOutput,
    SignalType,
    FlagReason,
)
from preciagro.packages.engines.feedback_learning.app.models.feedback_event import FeedbackEvent
from preciagro.packages.engines.feedback_learning.app.models.weighted_feedback import WeightedFeedback
from preciagro.packages.engines.feedback_learning.app.models.learning_signal import LearningSignal
from preciagro.packages.engines.feedback_learning.app.models.audit_trace import FeedbackAuditTrace, AuditStep


class TestUpstreamContracts:
    """Test upstream contract schemas."""
    
    def test_explicit_feedback_input(self):
        """Test ExplicitFeedbackInput schema."""
        input_data = ExplicitFeedbackInput(
            recommendation_id="rec-001",
            rating=4,
            feedback_category="helpful",
            comment="Great recommendation!",
            user_id="farmer-001",
            region_code="ZW",
        )
        
        assert input_data.recommendation_id == "rec-001"
        assert input_data.rating == 4
        assert input_data.feedback_category == "helpful"
    
    def test_explicit_feedback_rating_validation(self):
        """Test rating must be 1-5."""
        with pytest.raises(ValueError):
            ExplicitFeedbackInput(
                recommendation_id="rec-002",
                rating=0,  # Invalid
                feedback_category="helpful",
                user_id="farmer-002",
                region_code="ZW",
            )
        
        with pytest.raises(ValueError):
            ExplicitFeedbackInput(
                recommendation_id="rec-003",
                rating=6,  # Invalid
                feedback_category="helpful",
                user_id="farmer-003",
                region_code="ZW",
            )
    
    def test_implicit_feedback_input(self):
        """Test ImplicitFeedbackInput schema."""
        input_data = ImplicitFeedbackInput(
            recommendation_id="rec-010",
            viewed=True,
            view_duration_seconds=45.5,
            clicked_action=True,
            user_id="farmer-010",
            region_code="ZA",
        )
        
        assert input_data.viewed is True
        assert input_data.view_duration_seconds == 45.5
        assert input_data.clicked_action is True
    
    def test_outcome_feedback_input(self):
        """Test OutcomeFeedbackInput schema."""
        input_data = OutcomeFeedbackInput(
            recommendation_id="rec-020",
            action_executed=True,
            outcome_category="success",
            user_id="farmer-020",
            farm_id="farm-020",
            region_code="KE",
        )
        
        assert input_data.action_executed is True
        assert input_data.outcome_category == "success"
    
    def test_farmer_profile_context(self):
        """Test FarmerProfileContext schema."""
        profile = FarmerProfileContext(
            user_id="farmer-030",
            experience_level="expert",
            years_farming=15,
            verified_identity=True,
            trusted_contributor=True,
            region_code="ZW",
        )
        
        assert profile.experience_level == "expert"
        assert profile.years_farming == 15
    
    def test_recommendation_context(self):
        """Test RecommendationContext schema."""
        context = RecommendationContext(
            recommendation_id="rec-040",
            recommendation_type="treatment",
            confidence=0.85,
            model_id="cv-disease-v2",
            model_version="2.1.0",
            created_at=datetime.utcnow(),
            region_code="ZW",
        )
        
        assert context.confidence == 0.85
        assert context.model_id == "cv-disease-v2"


class TestDownstreamContracts:
    """Test downstream contract schemas."""
    
    def test_learning_signal_output(self):
        """Test LearningSignalOutput schema."""
        output = LearningSignalOutput(
            signal_type=SignalType.POSITIVE,
            signal_strength=0.75,
            source_feedback_ids=["fb-001", "fb-002"],
            recommendation_id="rec-050",
            target_engine="evaluation",
            region_scope="ZW",
            feedback_count=2,
            average_weight=0.8,
            confidence_score=0.7,
            feedback_window_start=datetime.utcnow(),
            feedback_window_end=datetime.utcnow(),
        )
        
        assert output.signal_type == SignalType.POSITIVE
        assert output.signal_strength == 0.75
        assert output.feedback_count == 2
    
    def test_flagged_feedback_output(self):
        """Test FlaggedFeedbackOutput schema."""
        output = FlaggedFeedbackOutput(
            feedback_id="fb-060",
            feedback_type="explicit",
            recommendation_id="rec-060",
            flag_reason=FlagReason.LOW_WEIGHT,
            flag_severity="medium",
            flag_description="Weight below threshold",
            computed_weight=0.25,
            feedback_summary="Rating: 3, Category: other",
        )
        
        assert output.flag_reason == FlagReason.LOW_WEIGHT
        assert output.flag_severity == "medium"
    
    def test_signal_type_enum(self):
        """Test SignalType enum values."""
        assert SignalType.POSITIVE.value == "positive"
        assert SignalType.NEGATIVE.value == "negative"
        assert SignalType.UNCERTAIN.value == "uncertain"
        assert SignalType.CONTRADICTION.value == "contradiction"
    
    def test_flag_reason_enum(self):
        """Test FlagReason enum values."""
        assert FlagReason.LOW_WEIGHT.value == "low_weight"
        assert FlagReason.CONTRADICTION.value == "contradiction"
        assert FlagReason.DUPLICATE.value == "duplicate"


class TestDataModels:
    """Test data model schemas."""
    
    def test_feedback_event_immutable(self):
        """Test FeedbackEvent is immutable (frozen)."""
        event = FeedbackEvent(
            recommendation_id="rec-070",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-070",
            raw_payload={"rating": 4},
        )
        
        # Should raise error when trying to modify
        with pytest.raises(Exception):  # ValidationError for frozen model
            event.rating = 5
    
    def test_weighted_feedback(self):
        """Test WeightedFeedback schema."""
        weighted = WeightedFeedback(
            source_feedback_id="fb-080",
            recommendation_id="rec-080",
            final_weight=0.72,
            base_confidence=0.6,
            farmer_experience_factor=0.8,
            historical_accuracy_factor=0.9,
            model_confidence_factor=0.7,
            environmental_stability_factor=0.85,
            trust_score=0.75,
            quality_score=0.8,
            region_code="ZW",
        )
        
        assert weighted.final_weight == 0.72
        assert weighted.is_flagged is False
    
    def test_learning_signal(self):
        """Test LearningSignal schema."""
        signal = LearningSignal(
            signal_type=SignalType.POSITIVE,
            signal_strength=0.8,
            source_feedback_ids=["fb-090"],
            recommendation_id="rec-090",
            target_engine="all",
            region_scope="ZW",
            feedback_count=1,
            average_weight=0.75,
            confidence_score=0.7,
            feedback_window_start=datetime.utcnow(),
            feedback_window_end=datetime.utcnow(),
        )
        
        assert signal.signal_type == SignalType.POSITIVE
        assert signal.is_routed is False
    
    def test_audit_step_immutable(self):
        """Test AuditStep is immutable (frozen)."""
        step = AuditStep(
            step_number=1,
            step_type="received",
            description="Received feedback",
        )
        
        # Should raise error when trying to modify
        with pytest.raises(Exception):
            step.step_number = 2
    
    def test_feedback_audit_trace(self):
        """Test FeedbackAuditTrace schema."""
        trace = FeedbackAuditTrace(
            source_feedback_id="fb-100",
            recommendation_id="rec-100",
        )
        
        assert trace.status == "processing"
        assert len(trace.steps) == 0
    
    def test_audit_trace_add_step(self):
        """Test adding steps to audit trace."""
        trace = FeedbackAuditTrace(
            source_feedback_id="fb-110",
            recommendation_id="rec-110",
        )
        
        step = trace.add_step(
            step_type="received",
            description="Received feedback from UX engine",
        )
        
        assert len(trace.steps) == 1
        assert step.step_number == 1
        assert step.step_type == "received"


class TestFeedbackType:
    """Test FeedbackType enum."""
    
    def test_feedback_types(self):
        """Test all feedback type values."""
        assert FeedbackType.EXPLICIT.value == "explicit"
        assert FeedbackType.IMPLICIT.value == "implicit"
        assert FeedbackType.OUTCOME.value == "outcome"
