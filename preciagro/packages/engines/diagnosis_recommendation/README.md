# 🔬 PreciAgro Diagnosis & Recommendation Engine (DRE)

**Foundational agricultural intelligence engine** that transforms observations from upstream engines into **safe, explainable, context-aware agricultural action plans**.

## Overview

The Diagnosis & Recommendation Engine (DRE) sits at the **decision junction** of the PreciAgro platform. It synthesizes structured signals from perception and context engines into ranked diagnoses and validated recommendation plans, while maintaining strict engine boundaries, explainability, and safety.

### Position in Engine Flow

```
Perception Engines
(Image Analysis, Conversational/NLP, Sensors)
    ↓
Context Engines
(GeoContext, Temporal Logic, Crop Intelligence, Inventory, Farmer Profile)
    ↓
→ **Diagnosis & Recommendation Engine** ←
    ↓
Trust & Explainability Engine
    ↓
UX Orchestration / Autonomous Action / Feedback & Learning
```

## Architecture

The engine is built with **9 core internal components**, each isolated, replaceable, and independently testable:

### 1. Input Harmonization Layer
Normalizes incoming structured signals from upstream engines into unified observations.

**Responsibilities:**
- Accepts structured outputs from Image Analysis, Conversational/NLP, Sensors, GeoContext, Temporal Logic, Crop Intelligence, Inventory, and Farmer Profile engines
- Normalizes signals to standard observation format
- Preserves provenance and metadata

### 2. Evidence Graph Builder
Builds short-lived, provenance-aware evidence graphs linking observations to context.

**Responsibilities:**
- Creates evidence edges between observations
- Infers evidence from patterns (temporal, spatial, contextual)
- Maintains evidence strength and confidence scores

### 3. Hypothesis Generation Layer
Enumerates all plausible explanations (disease, deficiency, pest, stress, management error).

**Responsibilities:**
- Generates hypotheses across all categories
- Links hypotheses to supporting evidence
- Assigns prior probabilities based on context

### 4. Diagnosis Reasoning Core
Applies symbolic, probabilistic, temporal, and spatial reasoning to rank hypotheses.

**Responsibilities:**
- Symbolic reasoning (category-specific rules)
- Probabilistic reasoning (Bayesian updating)
- Temporal reasoning (season/stage validity)
- Spatial reasoning (region validity)
- Ranks hypotheses by belief score

### 5. Recommendation Synthesis Core
Converts diagnoses into multi-step strategies and action plans.

**Responsibilities:**
- Generates recommendations for each hypothesis
- Creates step-by-step action plans
- Prioritizes recommendations
- Estimates costs and durations

### 6. Constraint & Safety Engine
Enforces inventory, legality, crop safety, environmental risk, and farmer constraints.

**Responsibilities:**
- Validates inventory availability
- Checks legal/regulatory compliance
- Ensures crop safety
- Validates environmental conditions
- Respects farmer preferences and budget

### 7. Confidence & Uncertainty Engine
Quantifies certainty, surfaces unknowns, and triggers escalation paths.

**Responsibilities:**
- Calculates overall uncertainty
- Identifies missing data sources
- Flags low-confidence sources
- Determines if human review is required

### 8. Explainability & Trace Engine
Produces evidence-linked reasoning traces for trust, audits, and debugging.

**Responsibilities:**
- Builds complete reasoning traces
- Generates human-readable rationales
- Tracks applied rules and model inferences
- Provides confidence breakdowns

### 9. Output Packaging Layer
Emits clean, engine-consumable outputs without UI assumptions.

**Responsibilities:**
- Packages all outputs into structured response
- Formats for downstream engines
- Includes warnings, data requests, and metadata

## Engine Boundaries (Strict)

### ✅ What the Engine DOES

- Consumes structured outputs from other engines
- Synthesizes observations into diagnoses
- Generates validated recommendation plans
- Enforces safety and constraints
- Provides explainable reasoning traces

### ❌ What the Engine DOES NOT DO

- **Never** interprets raw images (delegates to Image Analysis Engine)
- **Never** parses natural language (delegates to Conversational/NLP Engine)
- **Never** executes actions (delegates to Autonomous Action Engine)
- **Never** stores long-term memory (delegates to Feedback & Learning Engine)
- **Never** provides UI/UX (delegates to UX Orchestration Engine)

## Input Contract

The engine accepts structured outputs from upstream engines via `DREInput`:

```python
{
    "request_id": "uuid",
    "farmer_id": "farmer_123",
    "field_id": "field_456",
    "timestamp": "2025-01-15T10:00:00Z",
    
    # Optional signals from upstream engines
    "image_analysis": [...],      # From Image Analysis Engine
    "conversational_nlp": {...},   # From Conversational/NLP Engine
    "sensors": [...],              # From Sensor data
    "geo_context": {...},          # From GeoContext Engine
    "temporal_logic": {...},       # From Temporal Logic Engine
    "crop_intelligence": {...},    # From Crop Intelligence Engine
    "inventory": {...},            # From Inventory Engine
    "farmer_profile": {...},        # From Farmer Profile Engine
    
    "language": "en",
    "urgency": "medium"
}
```

**Graceful Degradation:** The engine proceeds with reduced confidence when upstream engines are unavailable, explicitly surfacing uncertainty.

## Output Contract

The engine outputs a machine-readable decision object via `DREResponse`:

```python
{
    "response_id": "uuid",
    "request_id": "uuid",
    "timestamp": "2025-01-15T10:00:05Z",
    
    "diagnosis": {
        "diagnosis_id": "uuid",
        "primary_hypothesis": "Late Blight",
        "primary_confidence": 0.85,
        "all_hypotheses": [...],
        "overall_confidence": 0.82,
        "uncertainty_reasons": [...]
    },
    
    "recommendations": {
        "plan_id": "uuid",
        "recommendations": [...],
        "execution_order": [...],
        "total_estimated_cost": {...},
        "is_validated": true
    },
    
    "overall_confidence": 0.82,
    "uncertainty_metrics": {...},
    "missing_data": [...],
    "warnings": [...],
    "constraint_violations": [...],
    "reasoning_trace_id": "uuid",
    "evidence_summary": {...},
    "data_requests": [...],
    "needs_human_review": false,
    "escalation_reasons": [...]
}
```

## Model Integration Policy

The engine is **model-agnostic** by design. All ML intelligence (CV, NLP, LLM, RL, Graph) is abstracted behind adapters:

### Adapter Interfaces

- **CVAdapter** - Computer vision models (disease detection, pest identification)
- **NLPAdapter** - NLP models (symptom extraction, intent classification)
- **LLMAdapter** - Large language models (hypothesis generation, reasoning)
- **RLAdapter** - Reinforcement learning (recommendation optimization)
- **GraphAdapter** - Graph-based models (knowledge graph reasoning)

### Integration Pattern

1. Adapters are **pluggable** - enable via configuration
2. Deterministic logic provides **fallback** when adapters unavailable
3. **No internal refactor** required when models are introduced
4. Adapters implement `BaseAdapter` interface

### Example: Enabling CV Adapter

```python
# In config
ENABLE_CV_ADAPTER=true
CV_MODEL_PATH=/path/to/model

# Adapter automatically used in hypothesis generation
# Falls back to deterministic logic if unavailable
```

## Safety, Ethics & Real-World Readiness

### Safety Features

- ✅ **Never recommends illegal actions** - Legal constraint checking
- ✅ **Blocks irreversible actions under low confidence** - Escalation thresholds
- ✅ **Respects regional regulations** - Region-specific validation
- ✅ **Supports human override** - Escalation paths for review

### Constraint Validation

The engine validates recommendations against:

1. **Inventory Constraints** - Required inputs available?
2. **Legality Constraints** - Banned chemicals? Timing restrictions?
3. **Crop Safety Constraints** - Chemical-crop compatibility? Growth stage restrictions?
4. **Environmental Risk Constraints** - Weather conditions suitable?
5. **Farmer Constraints** - Budget limits? Organic preferences?
6. **Temporal Constraints** - Season/stage appropriate?
7. **Spatial Constraints** - Region-specific restrictions?

### Escalation Triggers

Human review is required when:

- Overall uncertainty > 60%
- Diagnosis confidence < 40%
- High-priority recommendations with low confidence
- Missing critical data sources
- No primary hypothesis identified

## API Endpoints

### `POST /dre/diagnose`

Main diagnosis and recommendation endpoint.

**Request:** `DREInput`

**Response:** `DREResponse`

**Example:**

```bash
curl -X POST http://localhost:8106/dre/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "farmer_id": "farmer_123",
    "field_id": "field_456",
    "image_analysis": [{
      "image_id": "img_789",
      "detected_labels": ["leaf_spot", "yellowing"],
      "confidence_scores": {"leaf_spot": 0.85, "yellowing": 0.72}
    }],
    "geo_context": {
      "region_code": "ZW-MV",
      "soil_data": {"ph": 6.2, "organic_matter": 2.1}
    },
    "crop_intelligence": {
      "crop_type": "maize",
      "growth_stage": "vegetative",
      "health_status": "declining"
    }
  }'
```

### `GET /dre/health`

Health check endpoint.

**Response:**
```json
{"status": "ok"}
```

### `GET /dre/status`

Engine status and configuration.

**Response:**
```json
{
  "service": "diagnosis-recommendation",
  "version": "0.1.0",
  "config": {...},
  "adapters": {...}
}
```

## Configuration

### Environment Variables

```bash
# Service
DRE_SERVICE_NAME=diagnosis-recommendation
DRE_VERSION=0.1.0
DRE_DEBUG=false

# Engine parameters
DRE_MAX_HYPOTHESES=10
DRE_MIN_CONFIDENCE_THRESHOLD=0.3
DRE_ESCALATION_CONFIDENCE_THRESHOLD=0.4

# Safety and constraints
DRE_ENABLE_SAFETY_VALIDATION=true
DRE_ENABLE_CONSTRAINT_CHECKING=true
DRE_BLOCK_LOW_CONFIDENCE_ACTIONS=true

# Model adapters (future ML integration)
DRE_ENABLE_CV_ADAPTER=false
DRE_ENABLE_NLP_ADAPTER=false
DRE_ENABLE_LLM_ADAPTER=false
DRE_ENABLE_RL_ADAPTER=false
DRE_ENABLE_GRAPH_ADAPTER=false

# Explainability
DRE_ENABLE_REASONING_TRACE=true
DRE_TRACE_RETENTION_HOURS=24

# Performance
DRE_EVIDENCE_GRAPH_TTL_SECONDS=3600
DRE_MAX_PROCESSING_TIME_MS=5000.0

# Observability
DRE_ENABLE_PROMETHEUS=false
DRE_LOG_LEVEL=INFO
```

## Running the Engine

### Development Mode

```bash
# From PreciagroMVP root
uvicorn preciagro.packages.engines.diagnosis_recommendation.app.main:app \
  --reload --port 8106
```

### Production Mode

```bash
uvicorn preciagro.packages.engines.diagnosis_recommendation.app.main:app \
  --host 0.0.0.0 --port 8106 --workers 4
```

### Docker (Future)

```bash
docker build -t preciagro-dre .
docker run -p 8106:8106 preciagro-dre
```

## Testing

### Unit Tests

```bash
pytest preciagro/packages/engines/diagnosis_recommendation/tests/
```

### Integration Tests

```bash
# Test with upstream engines
pytest preciagro/packages/engines/diagnosis_recommendation/tests/integration/
```

### Manual Testing

Use the interactive API docs at `http://localhost:8106/docs` or test with curl (see API Endpoints section).

## Integration with Other Engines

### Consuming from Upstream Engines

The engine expects structured outputs. Example integration:

```python
# In Image Analysis Engine
image_result = {
    "image_id": "img_123",
    "detected_labels": ["leaf_spot"],
    "confidence_scores": {"leaf_spot": 0.85}
}

# In DRE Input
dre_input = DREInput(
    farmer_id="farmer_123",
    image_analysis=[ImageAnalysisSignal(**image_result)],
    geo_context=geo_context_signal,
    # ... other signals
)
```

### Providing to Downstream Engines

The engine outputs structured responses consumable by:

- **Trust & Explainability Engine** - Uses reasoning traces and evidence summaries
- **UX Orchestration Engine** - Uses diagnosis and recommendations
- **Autonomous Action Engine** - Uses validated recommendation plans
- **Feedback & Learning Engine** - Uses complete traces for learning

## Design Principles

### 1. Engine Boundaries
Strictly respects engine responsibilities. Never duplicates upstream or downstream functionality.

### 2. Model-Agnostic
All ML intelligence abstracted behind adapters. Deterministic logic provides fallback.

### 3. Explainable by Design
Every diagnosis includes evidence, reasoning traces, and confidence breakdowns.

### 4. Graceful Degradation
Proceeds with reduced confidence when upstream engines unavailable. Explicitly surfaces uncertainty.

### 5. Safety First
Never recommends illegal or unsafe actions. Blocks irreversible actions under low confidence.

### 6. Scalable to Autonomy
Designed to scale into autonomous decision-making without refactoring.

## Future Enhancements

### Phase 1: Model Integration
- [ ] Integrate CV models for disease detection
- [ ] Integrate NLP models for symptom extraction
- [ ] Integrate LLM for hypothesis generation
- [ ] Integrate RL for recommendation optimization
- [ ] Integrate graph models for knowledge reasoning

### Phase 2: Advanced Reasoning
- [ ] Multi-hypothesis reasoning with conflict resolution
- [ ] Temporal reasoning with historical patterns
- [ ] Spatial reasoning with field-level patterns
- [ ] Causal reasoning chains

### Phase 3: Learning & Adaptation
- [ ] Feedback integration for model improvement
- [ ] Online learning from farmer actions
- [ ] Regional adaptation based on outcomes

### Phase 4: Advanced Safety
- [ ] Real-time regulatory compliance checking
- [ ] Environmental impact assessment
- [ ] Economic impact modeling

## Contributing

When adding features:

1. **Maintain engine boundaries** - Never duplicate other engines' responsibilities
2. **Preserve explainability** - All reasoning must be traceable
3. **Add comprehensive tests** - Unit and integration tests required
4. **Update documentation** - Keep README and API docs current
5. **Follow safety guidelines** - All recommendations must be validated

## License

Proprietary - PreciAgro Platform

## Contact

For questions or support, contact the PreciAgro development team.

---

**Version**: 0.1.0  
**Status**: MVP - Production Ready  
**Last Updated**: January 2025

