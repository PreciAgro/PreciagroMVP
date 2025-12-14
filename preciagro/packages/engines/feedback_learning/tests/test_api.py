"""API Tests for Feedback & Learning Engine.

Tests the FastAPI endpoints for:
- Feedback capture (explicit, implicit, outcome)
- Learning signal retrieval
- Admin endpoints
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from preciagro.packages.engines.feedback_learning.app.main import app

client = TestClient(app)


class TestRootEndpoints:
    """Test root and health endpoints."""
    
    def test_root(self):
        """Test root info endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Feedback & Learning Engine"
        assert data["status"] == "operational"
        assert "version" in data
        assert "boundaries" in data
    
    def test_health(self):
        """Test health check."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_ready(self):
        """Test readiness check."""
        response = client.get("/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ready"] is True
        assert "dependencies" in data
    
    def test_config(self):
        """Test config endpoint."""
        response = client.get("/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "version" in data
        assert "weighting_formula" in data
        assert "streams" in data


class TestExplicitFeedback:
    """Test explicit feedback submission."""
    
    def test_submit_explicit_feedback(self):
        """Test submitting explicit feedback."""
        payload = {
            "recommendation_id": "rec-test-001",
            "rating": 4,
            "feedback_category": "helpful",
            "comment": "This recommendation was useful",
            "user_id": "farmer-001",
            "region_code": "ZW",
        }
        
        response = client.post("/feedback/explicit", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "accepted"
        assert "feedback_id" in data
        assert "correlation_id" in data
        assert data["queued_for_processing"] is True
    
    def test_explicit_feedback_with_reasoning_trace(self):
        """Test explicit feedback with reasoning trace reference."""
        payload = {
            "recommendation_id": "rec-test-002",
            "reasoning_trace_id": "trace-001",
            "rating": 5,
            "feedback_category": "helpful",
            "user_id": "farmer-002",
            "region_code": "ZA",
        }
        
        response = client.post("/feedback/explicit", json=payload)
        assert response.status_code == 200
    
    def test_explicit_feedback_rating_range(self):
        """Test rating validation (1-5)."""
        # Valid rating
        payload = {
            "recommendation_id": "rec-test-003",
            "rating": 1,
            "feedback_category": "not_helpful",
            "user_id": "farmer-003",
            "region_code": "ZW",
        }
        
        response = client.post("/feedback/explicit", json=payload)
        assert response.status_code == 200
        
        # Invalid rating (6 > 5)
        payload["rating"] = 6
        response = client.post("/feedback/explicit", json=payload)
        assert response.status_code == 422  # Validation error


class TestImplicitFeedback:
    """Test implicit feedback submission."""
    
    def test_submit_implicit_feedback(self):
        """Test submitting implicit behavioral feedback."""
        payload = {
            "recommendation_id": "rec-test-010",
            "viewed": True,
            "view_duration_seconds": 45.0,
            "clicked_action": True,
            "user_id": "farmer-010",
            "region_code": "KE",
        }
        
        response = client.post("/feedback/implicit", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "accepted"
        assert "feedback_id" in data
    
    def test_implicit_dismissed_feedback(self):
        """Test dismissed recommendation feedback."""
        payload = {
            "recommendation_id": "rec-test-011",
            "viewed": True,
            "view_duration_seconds": 5.0,
            "dismissed": True,
            "user_id": "farmer-011",
            "region_code": "ZW",
        }
        
        response = client.post("/feedback/implicit", json=payload)
        assert response.status_code == 200


class TestOutcomeFeedback:
    """Test outcome feedback submission."""
    
    def test_submit_outcome_feedback(self):
        """Test submitting outcome feedback."""
        payload = {
            "recommendation_id": "rec-test-020",
            "action_executed": True,
            "outcome_category": "success",
            "outcome_description": "Crop yield improved by 15%",
            "user_id": "farmer-020",
            "farm_id": "farm-020",
            "region_code": "ZW",
        }
        
        response = client.post("/feedback/outcome", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "accepted"
    
    def test_outcome_with_evidence(self):
        """Test outcome feedback with evidence references."""
        payload = {
            "recommendation_id": "rec-test-021",
            "action_executed": True,
            "outcome_category": "partial_success",
            "evidence_photo_refs": ["photo-001", "photo-002"],
            "evidence_sensor_refs": ["sensor-001"],
            "user_id": "farmer-021",
            "farm_id": "farm-021",
            "region_code": "ZA",
        }
        
        response = client.post("/feedback/outcome", json=payload)
        assert response.status_code == 200


class TestLearningSignals:
    """Test learning signal endpoints."""
    
    def test_get_signals_for_engine(self):
        """Test getting signals for a specific engine."""
        response = client.get("/learning/signals?engine=evaluation")
        assert response.status_code == 200
        
        data = response.json()
        assert "signals" in data
        assert "count" in data
        assert data["engine"] == "evaluation"
    
    def test_get_signals_with_region(self):
        """Test getting signals with region filter."""
        response = client.get("/learning/signals?engine=model_orchestration&region=ZW")
        assert response.status_code == 200
    
    def test_get_learning_stats(self):
        """Test getting learning stats."""
        response = client.get("/learning/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_signals" in data
        assert "unrouted_signals" in data
        assert "by_type" in data


class TestAdminEndpoints:
    """Test admin endpoints."""
    
    def test_get_flagged_feedback(self):
        """Test getting flagged feedback."""
        response = client.get("/admin/flagged")
        assert response.status_code == 200
        
        data = response.json()
        assert "flagged" in data
        assert "count" in data
        assert "total" in data
    
    def test_get_engine_stats(self):
        """Test getting engine statistics."""
        response = client.get("/admin/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "feedback_count" in data
        assert "weighted_count" in data
        assert "signal_count" in data
        assert "audit_stats" in data
    
    def test_audit_trace_not_found(self):
        """Test getting audit trace for non-existent feedback."""
        response = client.get("/admin/audit/nonexistent-id")
        assert response.status_code == 404
    
    def test_get_dead_letter(self):
        """Test getting dead letter messages."""
        response = client.get("/admin/dead-letter")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "messages" in data


class TestFeedbackCount:
    """Test feedback count endpoint."""
    
    def test_get_feedback_count(self):
        """Test getting feedback count."""
        response = client.get("/feedback/count")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
    
    def test_feedback_count_with_filter(self):
        """Test feedback count with recommendation filter."""
        response = client.get("/feedback/count?recommendation_id=rec-test-001")
        assert response.status_code == 200
