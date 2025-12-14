"""Tests for TEE API Endpoints."""

import pytest
from fastapi.testclient import TestClient

from preciagro.packages.engines.trust_explainability.app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns status."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["engine"] == "trust_explainability"
        assert "version" in data


class TestExplainEndpoint:
    """Tests for /explain endpoint."""
    
    def test_explain_tabular(self, client):
        """Test explaining tabular model output."""
        request = {
            "model_type": "tabular",
            "model_id": "xgb_v1",
            "model_outputs": {
                "diagnosis": "rust",
                "confidence": 0.85
            },
            "context": {
                "crop": "maize",
                "region": "ZW-HA"
            }
        }
        
        response = client.post("/api/v1/explain", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert "farmer_explanation" in data
        assert data["confidence"] > 0
    
    def test_explain_cv(self, client):
        """Test explaining CV model output."""
        request = {
            "model_type": "cv",
            "model_id": "classifier_v1",
            "model_outputs": {
                "prediction": "leaf_blight",
                "confidence": 0.92
            },
            "levels": ["farmer", "expert"]
        }
        
        response = client.post("/api/v1/explain", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["farmer_explanation"] is not None
        assert data["expert_explanation"] is not None
    
    def test_explain_with_safety_check(self, client):
        """Test explanation includes safety check."""
        request = {
            "model_type": "tabular",
            "model_id": "recommender_v1",
            "model_outputs": {
                "recommendation": "Apply fungicide",
                "action": "spray copper fungicide"
            },
            "include_safety_check": True
        }
        
        response = client.post("/api/v1/explain", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert "safety_status" in data
        assert data["safety_status"] in ["passed", "warning", "blocked"]


class TestExplainFastEndpoint:
    """Tests for /explain/fast endpoint."""
    
    def test_explain_fast(self, client):
        """Test fast one-liner explanation."""
        request = {
            "model_type": "tabular",
            "model_id": "test",
            "model_outputs": {
                "diagnosis": "powdery_mildew",
                "confidence": 0.75
            }
        }
        
        response = client.post("/api/v1/explain/fast", json=request)
        
        assert response.status_code == 200
        data = response.json()
        assert "explanation" in data
        assert len(data["explanation"]) > 0


class TestTraceEndpoint:
    """Tests for /trace endpoint."""
    
    def test_get_trace_not_found(self, client):
        """Test getting non-existent trace."""
        response = client.get("/api/v1/trace/nonexistent_trace_id")
        
        assert response.status_code == 404
    
    def test_get_trace_after_explain(self, client):
        """Test retrieving trace after explanation."""
        # First create an explanation
        explain_request = {
            "model_type": "tabular",
            "model_id": "test",
            "model_outputs": {"diagnosis": "test", "confidence": 0.5}
        }
        
        explain_response = client.post("/api/v1/explain", json=explain_request)
        assert explain_response.status_code == 200
        trace_id = explain_response.json()["trace_id"]
        
        # Then retrieve the trace
        trace_response = client.get(f"/api/v1/trace/{trace_id}")
        
        assert trace_response.status_code == 200
        data = trace_response.json()
        assert data["trace_id"] == trace_id


class TestFeedbackEndpoint:
    """Tests for /feedback endpoint."""
    
    def test_submit_feedback(self, client):
        """Test submitting feedback."""
        # First create an explanation to get a trace
        explain_request = {
            "model_type": "tabular",
            "model_id": "test",
            "model_outputs": {"diagnosis": "test", "confidence": 0.5}
        }
        explain_response = client.post("/api/v1/explain", json=explain_request)
        trace_id = explain_response.json()["trace_id"]
        
        # Submit feedback
        feedback = {
            "trace_id": trace_id,
            "feedback_type": "helpful",
            "rating": 5,
            "comment": "Very helpful explanation!"
        }
        
        response = client.post("/api/v1/feedback", json=feedback)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_feedback_stats(self, client):
        """Test getting feedback stats."""
        response = client.get("/api/v1/feedback/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_feedback" in data


class TestStrategiesEndpoint:
    """Tests for /strategies endpoint."""
    
    def test_list_strategies(self, client):
        """Test listing available strategies."""
        response = client.get("/api/v1/strategies")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "cv" in data
        assert "tabular" in data
        assert "llm" in data


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["engine"] == "trust_explainability"
        assert data["status"] == "running"
