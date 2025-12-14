# Feedback & Learning Engine (FLE)

> **Learning observer for PreciAgro** - Captures feedback, validates, weights, and routes learning signals to downstream engines.

## Overview

FLE is a **strictly bounded engine** in the PreciAgro multi-engine intelligence system. It exists **after intelligence is delivered**, not before - observing feedback and routing learning signals without influencing real-time decisions.

### What FLE Does
- ✅ Observe feedback (explicit, implicit, outcome)
- ✅ Validate feedback quality (duplicate, contradiction, noise detection)
- ✅ Weight feedback using a 5-factor formula
- ✅ Translate weighted feedback into typed learning signals
- ✅ Route signals to downstream engines (Evaluation, Model Orchestration, PIE)

### What FLE Does NOT Do
- ❌ Generate recommendations
- ❌ Call CV, NLP, or LLM models
- ❌ Retrain or fine-tune models
- ❌ Override decisions
- ❌ Delete historical data (append-only)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     UPSTREAM ENGINES                             │
│  UX Orchestration │ Diagnosis │ Trust │ Farmer Profile │ Farm   │
│    Inventory      │           │       │                │        │
└─────────────┬─────────────────┴───────┴────────────────┴────────┘
              │ Feedback Contracts
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FLE (Feedback & Learning)                     │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌────────┐ ┌────────┐│
│  │ Capture  │→│ Validation │→│ Weighting │→│ Signal │→│ Routing││
│  │ Service  │ │  Service   │ │  Service  │ │Service │ │ Service││
│  └──────────┘ └────────────┘ └───────────┘ └────────┘ └────────┘│
│                      │                                           │
│              ┌───────▼───────┐                                   │
│              │ Audit Service │ (Immutable traces)                │
│              └───────────────┘                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Learning Signals (Redis Streams)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DOWNSTREAM ENGINES                            │
│    Evaluation    │  Model Orchestration  │  PIE Lite  │  HITL   │
└─────────────────────────────────────────────────────────────────┘
```

## Weighting Formula

```
Weight = base_confidence × farmer_experience_factor × historical_accuracy_factor 
         × model_confidence_factor × environmental_stability_factor
```

Each factor is 0-1, producing a final weight of 0-1.

## API Endpoints

### Feedback (Inbound)
- `POST /feedback/explicit` - User ratings/comments
- `POST /feedback/implicit` - Behavioral signals
- `POST /feedback/outcome` - Action execution evidence

### Learning (Outbound)
- `GET /learning/signals?engine=<name>` - Pull signals for engine
- `POST /learning/export/model-orchestration` - Export for model training
- `POST /learning/export/evaluation` - Export for benchmarking

### Admin (Internal)
- `GET /admin/flagged` - Flagged feedback for review
- `POST /admin/review` - Submit review decision
- `GET /admin/audit/{feedback_id}` - Audit trace

## Quick Start

```bash
# Start the engine
cd preciagro/packages/engines/feedback_learning
python -m app.main

# Health check
curl http://localhost:8107/health
# {"status": "ok"}

# Submit feedback
curl -X POST http://localhost:8107/feedback/explicit \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_id": "rec-001",
    "rating": 4,
    "feedback_category": "helpful",
    "user_id": "farmer-001",
    "region_code": "ZW"
  }'
```

## Configuration

Environment variables (prefix `FLE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `FLE_DEBUG` | `false` | Debug mode |
| `FLE_DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection |
| `FLE_REDIS_URL` | `redis://localhost:6379/0` | Redis for streams |
| `FLE_CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker |

## Running Tests

```bash
cd preciagro
python -m pytest packages/engines/feedback_learning/tests/ -v
```

## Database Migrations

```bash
cd preciagro/packages/engines/feedback_learning
alembic upgrade head
```

## Technology Stack

- Python 3.11
- FastAPI (async)
- SQLAlchemy 2.0 async
- PostgreSQL (JSONB)
- Redis Streams
- Celery
- Pydantic v2
- Alembic
