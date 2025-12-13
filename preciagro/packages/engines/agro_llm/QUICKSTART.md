# AgroLLM Engine - Quick Start Guide

## Installation

```bash
cd preciagro/packages/engines/agro_llm
pip install -r requirements.txt
```

## Running the FastAPI Server

```bash
uvicorn app:app --host 0.0.0.0 --port 8104 --reload
```

## Example Request

```bash
curl -X POST "http://localhost:8104/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "farmer123",
    "field_id": "field456",
    "geo": {
      "lat": 7.2906,
      "lon": 80.6337,
      "region_code": "LK-01"
    },
    "timestamp": "2024-01-15T10:00:00Z",
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
      "use_for_training": false
    }
  }'
```

## Python API Usage

```python
import asyncio
from agro_llm import AgroLLMPipeline, ConfigLoader

async def main():
    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.load()
    
    # Initialize pipeline
    pipeline = AgroLLMPipeline(config=config)
    
    # Create request
    request = {
        "user_id": "farmer123",
        "geo": {
            "lat": 7.2906,
            "lon": 80.6337,
            "region_code": "LK-01"
        },
        "timestamp": "2024-01-15T10:00:00Z",
        "language": "en",
        "text": "My maize plants have yellow leaves",
        "crop": {
            "type": "maize",
            "variety": "local"
        },
        "soil": {
            "pH": 6.5,
            "moisture": 45.0
        }
    }
    
    # Process request
    response = await pipeline.process_request(request)
    
    # Print response
    print(f"Problem: {response.diagnosis_card.problem}")
    print(f"Confidence: {response.diagnosis_card.confidence}")
    print(f"Severity: {response.diagnosis_card.severity}")
    print(f"\nRecommended Actions:")
    for action in response.diagnosis_card.recommended_actions:
        print(f"  - {action.action}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

Edit `config/config.yaml` to configure:

- Model provider settings (mode, endpoint, API key)
- Safety rules (banned chemicals)
- Feature flags (enable/disable RAG, KG, etc.)
- Engine endpoints

## Testing

```bash
pytest tests/
```

## Health Check

```bash
curl http://localhost:8104/health
```

## Status

```bash
curl http://localhost:8104/status
```





