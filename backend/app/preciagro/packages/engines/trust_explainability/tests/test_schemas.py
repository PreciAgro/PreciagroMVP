"""Tests for TEE Contracts and Schemas."""

import pytest
from datetime import datetime
from uuid import uuid4

from preciagro.packages.engines.trust_explainability.contracts.v1.schemas import (
    EvidenceItem,
    ModelInfo,
    ExplanationArtifact,
    ConfidenceMetrics,
    SafetyViolation,
    SafetyCheckResult,
    ReasoningTrace,
    ExplanationRequest,
    ExplanationResponse,
    FeedbackPayload,
)
from preciagro.packages.engines.trust_explainability.contracts.v1.enums import (
    ExplanationLevel,
    UncertaintyType,
    SafetyStatus,
    EvidenceType,
    ExplanationStrategy,
    ViolationSeverity,
)


class TestEvidenceItem:
    """Tests for EvidenceItem schema."""

    def test_create_basic_evidence(self):
        """Test creating basic evidence item."""
        evidence = EvidenceItem(
            evidence_type=EvidenceType.IMAGE, source_engine="image_analysis", source_id="img_123"
        )

        assert evidence.evidence_type == EvidenceType.IMAGE
        assert evidence.source_engine == "image_analysis"
        assert evidence.source_id == "img_123"
        assert evidence.id is not None  # Auto-generated
        assert evidence.confidence == 1.0  # Default

    def test_evidence_with_all_fields(self):
        """Test evidence with all optional fields."""
        evidence = EvidenceItem(
            evidence_type=EvidenceType.SENSOR,
            source_engine="geo_context",
            source_id="sensor_456",
            content_ref="sensor://geo_context/sensor_456",
            content_hash="abc123",
            summary="Temperature: 25°C",
            confidence=0.95,
            freshness_hours=2.5,
            metadata={"unit": "celsius"},
        )

        assert evidence.summary == "Temperature: 25°C"
        assert evidence.confidence == 0.95
        assert evidence.freshness_hours == 2.5
        assert evidence.metadata["unit"] == "celsius"

    def test_evidence_serialization(self):
        """Test evidence serializes to dict correctly."""
        evidence = EvidenceItem(
            evidence_type=EvidenceType.TEXT, source_engine="conversational", source_id="txt_789"
        )

        data = evidence.model_dump()
        assert "evidence_type" in data
        assert data["evidence_type"] == "text"


class TestConfidenceMetrics:
    """Tests for ConfidenceMetrics schema."""

    def test_create_confidence_metrics(self):
        """Test creating confidence metrics."""
        metrics = ConfidenceMetrics(
            overall_confidence=0.85,
            uncertainty_type=UncertaintyType.EPISTEMIC,
            epistemic_uncertainty=0.15,
            aleatoric_uncertainty=0.05,
        )

        assert metrics.overall_confidence == 0.85
        assert metrics.uncertainty_type == UncertaintyType.EPISTEMIC

    def test_confidence_thresholds(self):
        """Test confidence threshold flags."""
        metrics = ConfidenceMetrics(
            overall_confidence=0.9,
            uncertainty_type=UncertaintyType.ALEATORIC,
            meets_high_threshold=True,
            meets_action_threshold=True,
        )

        assert metrics.meets_high_threshold is True
        assert metrics.meets_action_threshold is True


class TestSafetyCheckResult:
    """Tests for SafetyCheckResult schema."""

    def test_passed_safety_check(self):
        """Test safety check that passes."""
        result = SafetyCheckResult(
            status=SafetyStatus.PASSED,
            violations=[],
            blocking_count=0,
            warning_count=0,
            compliance_checked=True,
            safety_limits_checked=True,
        )

        assert result.status == SafetyStatus.PASSED
        assert len(result.violations) == 0

    def test_blocked_safety_check(self):
        """Test safety check with blocking violation."""
        violation = SafetyViolation(
            violation_type="banned_chemical",
            severity=ViolationSeverity.BLOCKING,
            message="Chemical 'DDT' is banned",
        )

        result = SafetyCheckResult(
            status=SafetyStatus.BLOCKED, violations=[violation], blocking_count=1
        )

        assert result.status == SafetyStatus.BLOCKED
        assert result.blocking_count == 1


class TestReasoningTrace:
    """Tests for ReasoningTrace schema."""

    def test_create_minimal_trace(self):
        """Test creating minimal reasoning trace."""
        trace = ReasoningTrace(request_id="req_123")

        assert trace.request_id == "req_123"
        assert trace.trace_id is not None
        assert trace.created_at is not None
        assert trace.engine_version == "1.0.0"
        assert trace.feedback_enabled is True

    def test_create_full_trace(self):
        """Test creating trace with all components."""
        evidence = EvidenceItem(
            evidence_type=EvidenceType.IMAGE, source_engine="image_analysis", source_id="img_123"
        )

        model = ModelInfo(
            model_id="classifier_v1",
            model_name="Disease Classifier",
            model_version="1.0.0",
            model_type="cv",
        )

        explanation = ExplanationArtifact(
            strategy=ExplanationStrategy.CV,
            level=ExplanationLevel.FARMER,
            content_type="text",
            content="This appears to be leaf blight.",
        )

        confidence = ConfidenceMetrics(
            overall_confidence=0.85, uncertainty_type=UncertaintyType.EPISTEMIC
        )

        safety = SafetyCheckResult(status=SafetyStatus.PASSED)

        trace = ReasoningTrace(
            request_id="req_123",
            evidence=[evidence],
            models=[model],
            explanations=[explanation],
            confidence=confidence,
            safety_check=safety,
            decision_id="diag_456",
            decision_type="diagnosis",
            decision_summary="Leaf blight detected",
        )

        assert len(trace.evidence) == 1
        assert len(trace.models) == 1
        assert len(trace.explanations) == 1
        assert trace.confidence.overall_confidence == 0.85
        assert trace.safety_check.status == SafetyStatus.PASSED


class TestExplanationRequest:
    """Tests for ExplanationRequest schema."""

    def test_create_request(self):
        """Test creating explanation request."""
        request = ExplanationRequest(
            model_type="tabular",
            model_id="xgb_v1",
            model_outputs={"diagnosis": "rust", "confidence": 0.75},
            context={"crop": "maize", "region": "ZW-HA"},
        )

        assert request.model_type == "tabular"
        assert request.model_id == "xgb_v1"
        assert request.model_outputs["diagnosis"] == "rust"
        assert request.language == "en"  # Default

    def test_request_with_options(self):
        """Test request with all options."""
        request = ExplanationRequest(
            model_type="cv",
            model_id="classifier_v1",
            model_outputs={"prediction": "leaf_spot"},
            levels=[ExplanationLevel.FARMER, ExplanationLevel.EXPERT],
            include_safety_check=True,
            include_confidence=True,
            language="sn",
        )

        assert len(request.levels) == 2
        assert request.include_safety_check is True
        assert request.language == "sn"


class TestFeedbackPayload:
    """Tests for FeedbackPayload schema."""

    def test_create_feedback(self):
        """Test creating feedback payload."""
        feedback = FeedbackPayload(
            trace_id="trace_123",
            feedback_type="helpful",
            rating=5,
            comment="Very clear explanation!",
        )

        assert feedback.trace_id == "trace_123"
        assert feedback.feedback_type == "helpful"
        assert feedback.rating == 5

    def test_feedback_with_correction(self):
        """Test feedback with suggested correction."""
        feedback = FeedbackPayload(
            trace_id="trace_456",
            feedback_type="incorrect",
            suggested_correction="This is actually northern corn leaf blight, not southern",
        )

        assert feedback.feedback_type == "incorrect"
        assert "northern corn leaf blight" in feedback.suggested_correction
