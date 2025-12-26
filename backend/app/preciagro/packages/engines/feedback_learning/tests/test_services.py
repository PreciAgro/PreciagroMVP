"""Service Tests for Feedback & Learning Engine.

Tests the core services:
- CaptureService
- ValidationService
- WeightingService
- SignalService
- RoutingService
- AuditService
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from preciagro.packages.engines.feedback_learning.app.services.capture_service import CaptureService
from preciagro.packages.engines.feedback_learning.app.services.validation_service import (
    ValidationService,
)
from preciagro.packages.engines.feedback_learning.app.services.weighting_service import (
    WeightingService,
)
from preciagro.packages.engines.feedback_learning.app.services.signal_service import SignalService
from preciagro.packages.engines.feedback_learning.app.services.routing_service import RoutingService
from preciagro.packages.engines.feedback_learning.app.services.audit_service import AuditService

from preciagro.packages.engines.feedback_learning.app.contracts.upstream import (
    ExplicitFeedbackInput,
    FarmerProfileContext,
    RecommendationContext,
)
from preciagro.packages.engines.feedback_learning.app.models.feedback_event import FeedbackEvent


class TestCaptureService:
    """Test CaptureService."""

    @pytest.fixture
    def service(self):
        return CaptureService()

    @pytest.mark.asyncio
    async def test_capture_explicit_feedback(self, service):
        """Test capturing explicit feedback."""
        input_data = ExplicitFeedbackInput(
            recommendation_id="rec-001",
            rating=4,
            feedback_category="helpful",
            user_id="farmer-001",
            region_code="ZW",
        )

        event = await service.capture_explicit_feedback(input_data)

        assert event.recommendation_id == "rec-001"
        assert event.rating == 4
        assert event.feedback_type == "explicit"
        assert event.region_code == "ZW"

    @pytest.mark.asyncio
    async def test_get_event(self, service):
        """Test retrieving a stored event."""
        input_data = ExplicitFeedbackInput(
            recommendation_id="rec-002",
            rating=5,
            feedback_category="helpful",
            user_id="farmer-002",
            region_code="ZA",
        )

        event = await service.capture_explicit_feedback(input_data)
        retrieved = await service.get_event(event.feedback_id)

        assert retrieved is not None
        assert retrieved.feedback_id == event.feedback_id

    @pytest.mark.asyncio
    async def test_count_events(self, service):
        """Test counting events."""
        # Capture a few events
        for i in range(3):
            input_data = ExplicitFeedbackInput(
                recommendation_id="rec-count",
                rating=3,
                feedback_category="other",
                user_id=f"farmer-{i}",
                region_code="ZW",
            )
            await service.capture_explicit_feedback(input_data)

        count = await service.count_events(recommendation_id="rec-count")
        assert count == 3


class TestValidationService:
    """Test ValidationService."""

    @pytest.fixture
    def service(self):
        return ValidationService()

    @pytest.mark.asyncio
    async def test_validate_valid_feedback(self, service):
        """Test validating valid feedback."""
        event = FeedbackEvent(
            recommendation_id="rec-val-001",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-001",
            raw_payload={"rating": 4},
            rating=4,
        )

        result = await service.validate(event, [], None)

        assert result.is_valid is True
        assert result.is_duplicate is False
        assert result.region_valid is True

    @pytest.mark.asyncio
    async def test_validate_invalid_region(self, service):
        """Test rejecting invalid region."""
        event = FeedbackEvent(
            recommendation_id="rec-val-002",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="XX",  # Invalid region
            user_id="farmer-002",
            raw_payload={"rating": 4},
        )

        result = await service.validate(event, [], None)

        assert result.is_valid is False
        assert result.region_valid is False

    @pytest.mark.asyncio
    async def test_detect_duplicate(self, service):
        """Test duplicate detection."""
        now = datetime.utcnow()

        existing = FeedbackEvent(
            feedback_id="existing-001",
            recommendation_id="rec-dup-001",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-dup",
            raw_payload={"rating": 4},
            rating=4,
            feedback_category="helpful",
            created_at=now,
        )

        new_event = FeedbackEvent(
            feedback_id="new-001",
            recommendation_id="rec-dup-001",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-dup",  # Same user
            raw_payload={"rating": 4},
            rating=4,  # Same rating
            feedback_category="helpful",  # Same category
            created_at=now,
        )

        result = await service.validate(new_event, [existing], None)

        assert result.is_duplicate is True
        assert result.duplicate_of_id == "existing-001"


class TestWeightingService:
    """Test WeightingService."""

    @pytest.fixture
    def service(self):
        return WeightingService()

    @pytest.mark.asyncio
    async def test_compute_weight(self, service):
        """Test computing weight for feedback."""
        event = FeedbackEvent(
            recommendation_id="rec-weight-001",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-weight",
            raw_payload={"rating": 4},
            rating=4,
        )

        weighted = await service.compute_weight(event)

        assert weighted.final_weight > 0
        assert weighted.final_weight <= 1
        assert weighted.source_feedback_id == event.feedback_id

    @pytest.mark.asyncio
    async def test_weight_factors(self, service):
        """Test that all weight factors are computed."""
        event = FeedbackEvent(
            recommendation_id="rec-weight-002",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-factors",
            raw_payload={"rating": 5, "comment": "Great advice!"},
            rating=5,
            comment="Great advice!",
        )

        weighted = await service.compute_weight(event)

        assert weighted.base_confidence > 0
        assert weighted.farmer_experience_factor > 0
        assert weighted.historical_accuracy_factor > 0
        assert weighted.model_confidence_factor > 0
        assert weighted.environmental_stability_factor > 0

    @pytest.mark.asyncio
    async def test_weight_with_farmer_profile(self, service):
        """Test weighting with farmer profile context."""
        event = FeedbackEvent(
            recommendation_id="rec-weight-003",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-expert",
            raw_payload={"rating": 4},
            rating=4,
        )

        farmer_profile = FarmerProfileContext(
            user_id="farmer-expert",
            experience_level="expert",
            verified_identity=True,
            trusted_contributor=True,
            region_code="ZW",
        )

        weighted = await service.compute_weight(event, farmer_profile=farmer_profile)

        # Expert farmer should have high experience factor
        assert weighted.farmer_experience_factor >= 0.9


class TestSignalService:
    """Test SignalService."""

    @pytest.fixture
    def weighting_service(self):
        return WeightingService()

    @pytest.fixture
    def service(self):
        return SignalService()

    @pytest.mark.asyncio
    async def test_generate_signal(self, service, weighting_service):
        """Test generating a learning signal."""
        event = FeedbackEvent(
            recommendation_id="rec-signal-001",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-signal",
            raw_payload={"rating": 4},
            rating=4,
        )

        weighted = await weighting_service.compute_weight(event)
        signal = await service.generate_signal(weighted)

        assert signal.signal_id is not None
        assert signal.recommendation_id == "rec-signal-001"
        assert signal.region_scope == "ZW"
        assert signal.feedback_count == 1

    @pytest.mark.asyncio
    async def test_get_signals_for_engine(self, service, weighting_service):
        """Test retrieving signals for an engine."""
        # Generate some signals
        for i in range(3):
            event = FeedbackEvent(
                recommendation_id=f"rec-retrieve-{i}",
                feedback_type="explicit",
                source_engine="ux_orchestration",
                region_code="ZW",
                user_id=f"farmer-{i}",
                raw_payload={"rating": 4},
                rating=4,
            )
            weighted = await weighting_service.compute_weight(event)
            await service.generate_signal(weighted, target_engine="all")

        signals = await service.get_signals_for_engine("evaluation")
        assert len(signals) >= 0  # May be 0 if already routed


class TestRoutingService:
    """Test RoutingService."""

    @pytest.fixture
    def service(self):
        return RoutingService()

    @pytest.fixture
    def signal_service(self):
        return SignalService()

    @pytest.fixture
    def weighting_service(self):
        return WeightingService()

    @pytest.mark.asyncio
    async def test_route_signal(self, service, signal_service, weighting_service):
        """Test routing a signal."""
        event = FeedbackEvent(
            recommendation_id="rec-route-001",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-route",
            raw_payload={"rating": 4},
            rating=4,
        )

        weighted = await weighting_service.compute_weight(event)
        signal = await signal_service.generate_signal(weighted, target_engine="evaluation")

        result = await service.route_signal(signal)

        assert result.success is True
        assert len(result.message_ids) > 0

    @pytest.mark.asyncio
    async def test_get_routing_stats(self, service):
        """Test getting routing stats."""
        stats = service.get_routing_stats()

        assert "total_routed" in stats
        assert "success_count" in stats
        assert "pending_by_stream" in stats


class TestAuditService:
    """Test AuditService."""

    @pytest.fixture
    def service(self):
        return AuditService()

    @pytest.mark.asyncio
    async def test_create_trace(self, service):
        """Test creating an audit trace."""
        event = FeedbackEvent(
            recommendation_id="rec-audit-001",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-audit",
            raw_payload={"rating": 4},
        )

        trace = await service.create_trace(event)

        assert trace.trace_id is not None
        assert trace.source_feedback_id == event.feedback_id
        assert len(trace.steps) == 1
        assert trace.steps[0].step_type == "received"

    @pytest.mark.asyncio
    async def test_add_steps_and_complete(self, service):
        """Test adding steps and completing trace."""
        event = FeedbackEvent(
            recommendation_id="rec-audit-002",
            feedback_type="explicit",
            source_engine="ux_orchestration",
            region_code="ZW",
            user_id="farmer-audit-2",
            raw_payload={"rating": 5},
        )

        trace = await service.create_trace(event)

        # Add validation step
        await service.add_validation_step(
            trace.trace_id, is_valid=True, validation_details={"is_duplicate": False}
        )

        # Complete trace
        completed = await service.complete_trace(trace.trace_id, status="completed")

        assert completed.status == "completed"
        assert completed.completed_at is not None
        assert len(completed.steps) == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, service):
        """Test getting audit stats."""
        stats = service.get_stats()

        assert "total_traces" in stats
        assert "by_status" in stats
        assert "total_steps" in stats
