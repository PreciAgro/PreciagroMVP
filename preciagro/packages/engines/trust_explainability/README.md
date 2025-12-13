# Trust & Explainability Engine (TEE)

**The moral and technical backbone of PreciAgro**

Model-agnostic explainability, confidence quantification, safety validation, and audit trail generation for AI-powered agricultural decisions.

## Overview

The Trust & Explainability Engine provides:

- **Multi-Strategy Explanations**: CV (Grad-CAM), tabular (SHAP), rule-based, and LLM summaries
- **Confidence Quantification**: Epistemic vs aleatoric uncertainty, ensemble disagreement
- **Safety Gate**: Pre-action validation against compliance rules, dosage limits, inventory
- **Reasoning Traces**: Immutable audit trails for every decision
- **Tiered Outputs**: Farmer-friendly, expert-level, and auditor-level explanations
- **Feedback Hooks**: Structured feedback collection for continuous improvement

## Quick Start

### Using the Engine Directly

```python
from preciagro.packages.engines.trust_explainability import (
    ExplanationService,
    ExplanationRequest,
    ExplanationLevel,
)

# Create service
service = ExplanationService()

# Create request
request = ExplanationRequest(
    model_type="tabular",
    model_id="disease_classifier_v1",
    model_outputs={
        "diagnosis": "leaf_blight",
        "confidence": 0.85
    },
    context={
        "crop": "maize",
        "region": "ZW-HA"
    },
    levels=[ExplanationLevel.FARMER, ExplanationLevel.EXPERT]
)

# Generate explanation
response = await service.explain(request)

print(response.farmer_explanation)
# "Based on your data, this appears to be leaf_blight (85% confidence). 
#  Key factors: soil moisture, temperature, growth stage."

print(response.safety_status)
# SafetyStatus.PASSED
```

### Using the Legacy Interface

```python
from preciagro.packages.engines.trust_explainability import run, status

# Get engine status
print(status())
# {'engine': 'trust_explainability', 'state': 'ready', 'version': '1.0.0', ...}

# Run explanation
result = run({
    "model_type": "cv",
    "model_outputs": {"prediction": "rust", "confidence": 0.9}
})
print(result["farmer_explanation"])
```

### Running as a Microservice

```bash
cd c:\Users\tinot\Desktop\PreciagroMVP
python -m preciagro.packages.engines.trust_explainability.app.main
```

Server starts at `http://localhost:8008`. API docs at `/docs`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/explain` | POST | Generate full explanation with trace |
| `/api/v1/explain/fast` | POST | Quick one-liner explanation |
| `/api/v1/trace/{id}` | GET | Retrieve reasoning trace |
| `/api/v1/feedback` | POST | Submit feedback |
| `/api/v1/strategies` | GET | List available strategies |
| `/api/v1/health` | GET | Health check |

### Example: Explain Endpoint

```bash
curl -X POST http://localhost:8008/api/v1/explain \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "tabular",
    "model_id": "dre_v1",
    "model_outputs": {
      "diagnosis": "powdery_mildew",
      "confidence": 0.78
    },
    "context": {
      "crop": "maize",
      "region": "ZW-HA"
    }
  }'
```

## Architecture

```
trust_explainability/
├── contracts/v1/       # Pydantic schemas and enums
├── core/               # Core logic modules
│   ├── evidence_collector.py
│   ├── explanation_router.py
│   ├── confidence_estimator.py
│   ├── safety_gate.py
│   └── reasoning_trace.py
├── strategies/         # Pluggable explanation strategies
│   ├── cv_explainer.py      # Grad-CAM
│   ├── tabular_explainer.py # SHAP
│   ├── rule_explainer.py    # Rule tracing
│   └── llm_summarizer.py    # LLM summaries
├── services/           # Business logic
├── api/                # FastAPI routes
├── app/                # Application entry
├── config/             # Settings
└── tests/              # Test suite
```

## Key Schemas

### ReasoningTrace

The canonical audit object containing all decision context:

```python
{
    "trace_id": "abc-123",
    "request_id": "req-456",
    "evidence": [...],           # Data provenance
    "models": [...],             # Models involved
    "explanations": [...],       # Generated explanations
    "confidence": {...},         # Uncertainty metrics
    "safety_check": {...},       # Validation result
    "decision_summary": "...",
    "feedback_url": "/api/v1/feedback?trace_id=abc-123"
}
```

### SafetyCheckResult

Pre-action validation:

```python
{
    "status": "passed" | "warning" | "blocked",
    "violations": [
        {
            "type": "banned_chemical",
            "severity": "blocking",
            "message": "Chemical 'DDT' is banned"
        }
    ]
}
```

## Configuration

Environment variables (prefix `TEE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `TEE_CONFIDENCE_THRESHOLD_HIGH` | 0.8 | High confidence threshold |
| `TEE_SAFETY_GATE_STRICT` | true | Block on warnings |
| `TEE_ENABLE_SHAP` | true | Enable SHAP explanations |
| `TEE_ENABLE_GRADCAM` | true | Enable Grad-CAM saliency |
| `TEE_API_PORT` | 8008 | API server port |

## Testing

```bash
# Run all TEE tests
pytest preciagro/packages/engines/trust_explainability/tests/ -v

# Run specific test file
pytest preciagro/packages/engines/trust_explainability/tests/test_api.py -v
```

## Language Support

Explanations support multiple languages:
- `en` - English (default)
- `sn` - Shona
- `pl` - Polish

Specify via `language` field in requests.

## Phase 2 Features (Coming Soon)

- Counterfactual explanations
- Example-based retrieval
- Cryptographic audit signatures
- Advanced uncertainty calibration
