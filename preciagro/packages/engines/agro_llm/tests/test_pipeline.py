"""Tests for AgroLLM Pipeline."""

import pytest
from datetime import datetime

from ..pipeline import AgroLLMPipeline
from ..contracts.v1.schemas import FarmerRequest, GeoContext
from ..config import ConfigLoader


@pytest.fixture
def sample_request():
    """Sample farmer request for testing."""
    return {
        "user_id": "test_user_123",
        "field_id": "field_456",
        "geo": {
            "lat": 7.2906,
            "lon": 80.6337,
            "region_code": "LK-01"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "language": "en",
        "text": "My maize plants are showing yellow leaves. What should I do?",
        "images": [],
        "image_features": [],
        "soil": {
            "pH": 6.5,
            "moisture": 45.0
        },
        "crop": {
            "type": "maize",
            "variety": "local"
        },
        "weather": {
            "temp": 28.0,
            "humidity": 75.0
        },
        "session_context": [],
        "consent": {
            "use_for_training": False
        }
    }


@pytest.mark.asyncio
async def test_pipeline_process_request(sample_request):
    """Test pipeline processing a request."""
    config_loader = ConfigLoader()
    config = config_loader.load()
    pipeline = AgroLLMPipeline(config=config)
    
    response = await pipeline.process_request(sample_request)
    
    assert response is not None
    assert response.id is not None
    assert response.generated_text is not None
    assert response.diagnosis_card is not None
    assert response.diagnosis_card.problem is not None
    assert 0.0 <= response.diagnosis_card.confidence <= 1.0
    assert response.diagnosis_card.severity in ["low", "medium", "high"]


@pytest.mark.asyncio
async def test_pipeline_with_images(sample_request):
    """Test pipeline with image features."""
    sample_request["images"] = ["img_1", "img_2"]
    sample_request["image_features"] = [
        {
            "id": "img_1",
            "embedding": [0.1] * 128,
            "labels": ["leaf", "yellow"]
        }
    ]
    
    config_loader = ConfigLoader()
    config = config_loader.load()
    pipeline = AgroLLMPipeline(config=config)
    
    response = await pipeline.process_request(sample_request)
    
    assert response is not None
    assert response.diagnosis_card is not None


def test_input_normalization(sample_request):
    """Test input normalization."""
    from ..normalization import InputNormalizer
    
    normalizer = InputNormalizer()
    request = normalizer.normalize(sample_request)
    
    assert isinstance(request, FarmerRequest)
    assert request.user_id == "test_user_123"
    assert request.geo.lat == 7.2906
    assert request.geo.region_code == "LK-01"







