# AgroLLM Engine

Core agricultural language model engine for PreciAgro MVP.

## Overview

The AgroLLM Engine is a production-architecture-ready language model system that provides agricultural advice and recommendations to farmers. It integrates multiple data sources, enforces safety constraints, and generates structured, explainable responses.

## Architecture

The engine follows a modular pipeline architecture:

```
Input Normalization → Multi-modal Fusion → RAG/KG/Local Context → 
LLM Generation → Reasoning Graph Validation → Safety Constraints → 
Structured Output → Feedback Collection
```

## Key Components

### 1. Core LLM Wrapper (`core/`)
- Supports multiple deployment modes: `pretrained`, `self_hosted`, `future_finetuned`
- Handles prompt building and response generation
- Structured JSON output formatting

### 2. Reasoning Graph Engine (`reasoning_graph/`)
- Validates LLM output for contradictions
- Checks for illegal actions and unsafe sequences
- Builds reasoning graphs for explainability

### 3. Safety & Domain Constraints (`safety/`)
- Validates banned chemicals
- Checks season compatibility
- Validates soil × crop compatibility
- Enforces weather constraints

### 4. RAG Adapter (`rag/`)
- Vector database integration (placeholder for MVP)
- Context retrieval for agricultural knowledge
- Document ranking and scoring

### 5. Knowledge Graph Adapter (`knowledge_graph/`)
- Agricultural knowledge graph queries
- Entity and relationship extraction
- Subgraph retrieval

### 6. Local Intelligence Adapter (`local/`)
- Region-specific rules and practices
- Crop variety-specific guidance
- JSON-based rule storage

### 7. Multi-modal Fusion (`fusion/`)
- Combines image embeddings, soil data, weather data
- Unified context dictionary generation
- Session context integration

### 8. Structured Output Generator (`output/`)
- Enforces strict JSON schema
- Validates response structure
- Generates diagnosis cards and recommendations

### 9. Input Normalization (`normalization/`)
- Validates and normalizes units
- Timestamp normalization (ISO8601)
- Geographic field validation

### 10. Integration Clients (`clients/`)
- Interfaces for all PreciAgro engines:
  - ImageAnalysisClient
  - GeoContextClient
  - TemporalLogicClient
  - CropIntelligenceClient
  - DataIntegrationClient
  - InventoryClient
  - SecurityAccessClient
  - OrchestratorClient

### 11. Feedback & Learning Hooks (`feedback/`)
- Interaction logging
- Feedback collection
- Event emission for downstream processing

### 12. Configuration System (`config/`)
- YAML-based configuration
- Model provider settings
- Safety rules configuration
- Feature flags

## API

### FastAPI Endpoints

- `POST /generate` - Generate response from raw request dictionary
- `POST /v1/generate` - Generate response with Pydantic validation
- `GET /health` - Health check
- `GET /status` - Engine status and configuration

### Request Schema

See `contracts/v1/schemas.py` for `FarmerRequest` schema.

### Response Schema

See `contracts/v1/schemas.py` for `AgroLLMResponse` schema.

## Configuration

Configuration is managed via `config/config.yaml`. Key settings:

- `model_provider`: LLM mode and settings
- `safety_rules`: Banned chemicals and safety constraints
- `region_rules`: Local rules directory
- `orchestrator`: Orchestrator integration settings
- `feature_flags`: Enable/disable features

## Usage

### Python API

```python
from agro_llm import AgroLLMPipeline, ConfigLoader

# Load configuration
config_loader = ConfigLoader()
config = config_loader.load()

# Initialize pipeline
pipeline = AgroLLMPipeline(config=config)

# Process request
request = {
    "user_id": "user123",
    "geo": {"lat": 7.29, "lon": 80.63, "region_code": "LK-01"},
    "timestamp": "2024-01-01T00:00:00Z",
    "language": "en",
    "text": "My maize plants have yellow leaves",
    "crop": {"type": "maize", "variety": "local"},
    # ... other fields
}

response = await pipeline.process_request(request)
```

### FastAPI Server

```bash
uvicorn agro_llm.app:app --host 0.0.0.0 --port 8104
```

## Development

### Project Structure

```
agro_llm/
├── core/                 # LLM wrapper
├── reasoning_graph/      # Reasoning validation
├── safety/              # Safety constraints
├── rag/                 # RAG adapter
├── knowledge_graph/     # KG adapter
├── local/               # Local intelligence
├── fusion/              # Multi-modal fusion
├── output/              # Structured output
├── normalization/       # Input normalization
├── clients/             # Engine integration clients
├── feedback/            # Feedback hooks
├── config/              # Configuration
├── contracts/v1/        # Schemas and contracts
├── local_rules/         # Local rule JSON files
├── tests/               # Tests
├── pipeline.py          # Main pipeline
├── app.py               # FastAPI application
└── __init__.py          # Module exports
```

### Testing

```bash
pytest tests/
```

## MVP Status

This is an MVP implementation with placeholder components:

- ✅ All modules implemented
- ✅ All interfaces defined
- ✅ Pipeline wired together
- ✅ FastAPI application ready
- ⚠️ LLM integration: Placeholder (ready for model integration)
- ⚠️ Vector DB: Placeholder (ready for Qdrant/Weaviate integration)
- ⚠️ Knowledge Graph: Placeholder (ready for KG integration)
- ⚠️ Client integrations: Stub implementations (ready for real clients)

## Next Steps

1. Integrate actual LLM model (pretrained or self-hosted)
2. Connect to vector database for RAG
3. Integrate with knowledge graph service
4. Implement real client connections to other engines
5. Add telemetry and monitoring
6. Enhance safety rules with more comprehensive checks
7. Add model fine-tuning pipeline

## License

Part of PreciAgro MVP.







