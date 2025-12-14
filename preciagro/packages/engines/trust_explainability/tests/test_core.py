"""Tests for TEE Core Modules."""

import pytest
from unittest.mock import MagicMock, patch

from preciagro.packages.engines.trust_explainability.core.evidence_collector import (
    EvidenceCollector,
)
from preciagro.packages.engines.trust_explainability.core.confidence_estimator import (
    ConfidenceEstimator,
)
from preciagro.packages.engines.trust_explainability.core.safety_gate import (
    SafetyGate,
)
from preciagro.packages.engines.trust_explainability.core.reasoning_trace import (
    ReasoningTraceBuilder,
    TraceStore,
)
from preciagro.packages.engines.trust_explainability.contracts.v1.schemas import (
    ExplanationRequest,
    EvidenceItem,
    ModelInfo,
    ConfidenceMetrics,
)
from preciagro.packages.engines.trust_explainability.contracts.v1.enums import (
    EvidenceType,
    UncertaintyType,
    SafetyStatus,
    ViolationSeverity,
)


class TestEvidenceCollector:
    """Tests for EvidenceCollector."""
    
    def test_collect_from_request(self):
        """Test collecting evidence from request."""
        collector = EvidenceCollector()
        
        request = ExplanationRequest(
            model_type="tabular",
            model_id="test_model",
            model_outputs={"diagnosis": "rust", "confidence": 0.8},
            context={"crop": "maize"}
        )
        
        evidence = collector.collect(request)
        
        assert len(evidence) >= 1  # At least model output evidence
        assert any(e.evidence_type == EvidenceType.MODEL_OUTPUT for e in evidence)
    
    def test_collect_with_preloaded_evidence(self):
        """Test collecting with pre-provided evidence."""
        collector = EvidenceCollector()
        
        request = ExplanationRequest(
            model_type="cv",
            model_id="classifier",
            model_outputs={"prediction": "leaf_spot"},
            evidence=[
                {"type": "image", "source_engine": "image_analysis", "source_id": "img_1"}
            ]
        )
        
        evidence = collector.collect(request)
        
        assert any(e.evidence_type == EvidenceType.IMAGE for e in evidence)
    
    def test_add_image_evidence(self):
        """Test adding image evidence."""
        collector = EvidenceCollector()
        
        evidence = collector.add_image_evidence(
            image_id="img_123",
            summary="Crop image showing leaf spots"
        )
        
        assert evidence.evidence_type == EvidenceType.IMAGE
        assert evidence.source_id == "img_123"
        assert "leaf spots" in evidence.summary
    
    def test_add_sensor_evidence(self):
        """Test adding sensor evidence."""
        collector = EvidenceCollector()
        
        sensor_data = {
            "type": "temperature",
            "value": 25.5,
            "unit": "°C"
        }
        
        evidence = collector.add_sensor_evidence(
            sensor_data=sensor_data,
            sensor_id="temp_001"
        )
        
        assert evidence.evidence_type == EvidenceType.SENSOR
        assert "25.5" in evidence.summary


class TestConfidenceEstimator:
    """Tests for ConfidenceEstimator."""
    
    def test_estimate_single_model(self):
        """Test estimating confidence from single model."""
        estimator = ConfidenceEstimator()
        
        metrics = estimator.estimate([
            {"confidence": 0.85, "prediction": "rust"}
        ])
        
        assert metrics.overall_confidence > 0
        assert metrics.uncertainty_type in [
            UncertaintyType.EPISTEMIC,
            UncertaintyType.ALEATORIC,
            UncertaintyType.MIXED
        ]
    
    def test_estimate_ensemble(self):
        """Test estimating confidence from ensemble."""
        estimator = ConfidenceEstimator()
        
        metrics = estimator.estimate([
            {"confidence": 0.9},
            {"confidence": 0.85},
            {"confidence": 0.88}
        ])
        
        assert metrics.num_ensemble_members == 3
        assert metrics.ensemble_agreement is not None
    
    def test_estimate_with_disagreement(self):
        """Test detecting ensemble disagreement."""
        estimator = ConfidenceEstimator()
        
        # Models with high disagreement
        metrics = estimator.estimate([
            {"confidence": 0.95},
            {"confidence": 0.3},
            {"confidence": 0.6}
        ])
        
        assert metrics.epistemic_uncertainty > 0.3  # High epistemic
    
    def test_check_threshold(self):
        """Test confidence threshold checking."""
        estimator = ConfidenceEstimator()
        
        passes, msg = estimator.check_threshold(0.9, "recommendation")
        assert passes is True
        
        passes, msg = estimator.check_threshold(0.1, "treatment")
        assert passes is False
    
    def test_get_confidence_level(self):
        """Test confidence level categorization."""
        estimator = ConfidenceEstimator()
        
        assert estimator.get_confidence_level(0.9) == "high"
        assert estimator.get_confidence_level(0.6) == "medium"
        assert estimator.get_confidence_level(0.3) == "low"


class TestSafetyGate:
    """Tests for SafetyGate."""
    
    def test_validate_safe_recommendation(self):
        """Test validating safe recommendation."""
        gate = SafetyGate()
        
        result = gate.validate(
            recommendation={"action": "Apply organic fertilizer", "dose": "5kg"},
            context={"region": "ZW-HA", "crop": "maize"}
        )
        
        assert result.status in [SafetyStatus.PASSED, SafetyStatus.WARNING]
        assert result.blocking_count == 0
    
    def test_detect_banned_chemical(self):
        """Test detecting banned chemical."""
        gate = SafetyGate()
        
        result = gate.validate(
            recommendation={"action": "Apply DDT pesticide"},
            context={"region": "ZW-HA"}
        )
        
        assert result.status == SafetyStatus.BLOCKED
        assert result.blocking_count > 0
        assert any("DDT" in v.message for v in result.violations)
    
    def test_check_dosage_limits(self):
        """Test checking dosage limits."""
        gate = SafetyGate()
        
        result = gate.validate(
            recommendation={
                "action": "Apply glyphosate herbicide",
                "dose": "10"  # Exceeds max of 4.0 L/ha
            },
            context={}
        )
        
        assert result.status == SafetyStatus.BLOCKED
        assert any(v.violation_type == "dosage_exceeded" for v in result.violations)
    
    def test_missing_ppe_warning(self):
        """Test detecting missing PPE warning."""
        gate = SafetyGate()
        
        result = gate.validate(
            recommendation={"action": "Spray pesticide on crops"},
            context={}
        )
        
        assert any(v.violation_type == "missing_ppe_warning" for v in result.violations)


class TestReasoningTraceBuilder:
    """Tests for ReasoningTraceBuilder."""
    
    def test_build_minimal_trace(self):
        """Test building minimal trace."""
        builder = ReasoningTraceBuilder()
        
        trace = builder.create("req_123").build()
        
        assert trace.request_id == "req_123"
        assert trace.trace_id is not None
    
    def test_build_full_trace(self):
        """Test building trace with all components."""
        builder = ReasoningTraceBuilder()
        
        evidence = EvidenceItem(
            evidence_type=EvidenceType.IMAGE,
            source_engine="image_analysis",
            source_id="img_1"
        )
        
        model = ModelInfo(
            model_id="clf_v1",
            model_name="Classifier",
            model_version="1.0",
            model_type="cv"
        )
        
        confidence = ConfidenceMetrics(
            overall_confidence=0.85,
            uncertainty_type=UncertaintyType.EPISTEMIC
        )
        
        trace = (
            builder
            .create("req_456")
            .add_input_ref("image", "img_1")
            .add_model(model)
            .add_evidence([evidence])
            .set_confidence(confidence)
            .set_decision("diag_789", "diagnosis", "Leaf blight")
            .build()
        )
        
        assert trace.request_id == "req_456"
        assert len(trace.models) == 1
        assert len(trace.evidence) == 1
        assert trace.confidence.overall_confidence == 0.85
        assert trace.decision_summary == "Leaf blight"
    
    def test_trace_signature(self):
        """Test generating trace signature."""
        builder = ReasoningTraceBuilder()
        
        trace = builder.create("req_sig").build()
        signature = builder.sign(trace)
        
        assert signature.startswith("sha256:")
        assert len(signature) > 10


class TestTraceStore:
    """Tests for TraceStore."""
    
    def test_store_and_retrieve(self):
        """Test storing and retrieving trace."""
        store = TraceStore()
        builder = ReasoningTraceBuilder()
        
        trace = builder.create("req_store").build()
        trace_id = store.store(trace)
        
        retrieved = store.get(trace_id)
        
        assert retrieved is not None
        assert retrieved.request_id == "req_store"
    
    def test_get_by_request(self):
        """Test getting traces by request ID."""
        store = TraceStore()
        builder = ReasoningTraceBuilder()
        
        request_id = "req_multi"
        
        # Store multiple traces for same request
        trace1 = builder.create(request_id).build()
        trace2 = builder.create(request_id).build()
        store.store(trace1)
        store.store(trace2)
        
        traces = store.get_by_request(request_id)
        
        assert len(traces) == 2
    
    def test_delete_trace(self):
        """Test deleting trace."""
        store = TraceStore()
        builder = ReasoningTraceBuilder()
        
        trace = builder.create("req_del").build()
        trace_id = store.store(trace)
        
        deleted = store.delete(trace_id)
        assert deleted is True
        
        retrieved = store.get(trace_id)
        assert retrieved is None
