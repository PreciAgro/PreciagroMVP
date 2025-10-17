```markdown
# 🌱 Crop Intelligence Engine (CIE) - MVP

## Overview

The **Crop Intelligence Engine (CIE)** is an explainable agronomic recommendation system that provides accurate, trustable, and region-relevant advice for farmers. It tracks crop growth stages, manages water and nutrient timing, assesses disease risks, and generates actionable recommendations.

## 🎯 MVP Goals

### Functional Capabilities
- **Track crop growth stage**: Determine current stage (±1 accuracy) using planting date + GDD + NDVI/EVI trend
- **Water management**: Calculate ET₀/ETc (FAO-56) or use simple soil-bucket model
- **Nitrogen timing**: Identify correct window for N top-dress with timing explanations
- **Disease/pest warnings**: Flag "Low/Medium/High" risk from weather and humidity data
- **Yield outlook**: Provide P10/P50/P90 yield bands
- **Explainable actions**: Generate action cards with What/Why/Risk/Alternatives/Uncertainty
- **Farmer feedback**: Capture Accepted/Delayed/Ignored for every recommendation

### Technical Implementation
- Modular FastAPI service with clean endpoints
- In-memory storage (replaceable with Postgres/Redis)
- Physics-based logic with safe pretrained ML
- 100% explainability - no hidden model outputs
- Stateless components ready for API Gateway integration
- Event logging for Product Insights Engine (PIE)

## 📂 Project Structure

```

```rust
crop_intelligence/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── router.py              # API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic models
│   ├── repos/
│   │   ├── __init__.py
│   │   ├── typing.py              # Type definitions
│   │   └── events.py              # Event repository
│   ├── services/
│   │   ├── __init__.py
│   │   ├── field_state_tracker.py # Field state management
│   │   ├── phenology_water.py     # Stage estimation & water
│   │   ├── nutrient_timing.py     # Nutrient recommendations
│   │   ├── health_risk.py         # Disease/pest risk assessment
│   │   ├── yield_outlook.py       # Yield estimation
│   │   ├── decision_ranker.py     # Action ranking
│   │   └── learning_hooks.py      # Event capture for learning
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_smoke.py              # Smoke tests
├── pyproject.toml                 # Dependencies
└── README.md                      # This file

```

```

## 🚀 API Endpoints

### 1. POST `/cie/field/register`
Register a new field with crop and management details.

**Request:**
```json
{
  "field_id": "f_1",
  "boundary_geojson": {"type": "Polygon", "coordinates": []},
  "crop": "maize",
  "variety": "SC627",
  "planting_date": "2025-11-10",
  "irrigation_access": "none",
  "target_yield_band": "2-4 t/ha",
  "budget_class": "low"
}
```

### 2. POST `/cie/field/telemetry`
Submit telemetry data (weather, vegetation indices, soil).

**Request:**

```json
{
  "field_id": "f_1",
  "weather": [
    {"ts": "2025-12-01T00:00:00", "tmax": 28.5, "tmin": 18.2, "rain": 5.0, "rh": 75}
  ],
  "vi": [
    {"date": "2025-12-01", "ndvi": 0.3, "quality": "good"},
    {"date": "2025-12-10", "ndvi": 0.34, "quality": "good"}
  ],
  "soil": {
    "src": "soilgrids",
    "texture": "loam",
    "whc_mm": 140,
    "uncertainty": "±15%"
  }
}
```

### 3. GET `/cie/field/state?field_id=f_1`
Get current field state including stage, vigor trend, and risks.

**Response:**

```json
{
  "stage": "vegetative",
  "stage_confidence": 0.6,
  "vigor_trend": "increasing",
  "risks": [
    {"type": "late_blight", "level": "medium", "confidence": 0.6}
  ]
}
```

### 4. GET `/cie/field/actions?field_id=f_1`
Get recommended actions for a field.

**Response:**

```json
{
  "items": [
    {
      "action_id": "a_f_1_n",
      "action": "N_Topdress",
      "impact_score": 0.8,
      "why": ["vegetative stage: N demand rising", "rain window ≥10mm"],
      "alternatives": [],
      "uncertainty": "medium",
      "window_start": "soon",
      "window_end": "+3d"
    }
  ]
}
```

### 5. POST `/cie/feedback`
Submit farmer feedback on recommended actions.

**Request:**

```json
{
  "field_id": "f_1",
  "action_id": "a_f_1_n",
  "decision": "accepted",
  "note": "Applied 50kg N per hectare"
}
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- pip

### Install Dependencies

```powershell
# From the crop_intelligence directory
pip install fastapi uvicorn pydantic pydantic-settings numpy pandas scikit-learn httpx
```

Or using the pyproject.toml:

```powershell
pip install -e .
```

## 🏃 Running the Service

### Development Mode

```powershell
# From the PreciagroMVP root directory
uvicorn preciagro.packages.engines.crop_intelligence.app.main:app --reload --port 8082
```

The service will be available at:
- API: http://localhost:8082
- Interactive docs: http://localhost:8082/docs
- OpenAPI schema: http://localhost:8082/openapi.json

### Production Mode

```powershell
uvicorn preciagro.packages.engines.crop_intelligence.app.main:app --host 0.0.0.0 --port 8082 --workers 4
```

## 🧪 Testing

### Run Smoke Tests

```powershell
# From the PreciagroMVP root directory
pytest preciagro/packages/engines/crop_intelligence/tests/test_smoke.py -v
```

### Manual Testing

Use the interactive API docs at http://localhost:8082/docs or test with curl:

```powershell
# Health check
curl http://localhost:8082/

# Register field
curl -X POST http://localhost:8082/cie/field/register `
  -H "Content-Type: application/json" `
  -d '{
    "field_id": "test_field_1",
    "boundary_geojson": {"type": "Polygon", "coordinates": []},
    "crop": "maize",
    "planting_date": "2025-11-10",
    "irrigation_access": "limited",
    "budget_class": "medium"
  }'
```

## 📊 Operational KPIs (MVP Success Criteria)

| KPI | Target |
|-----|--------|
| Stage accuracy | ≥ 80% within ± 1 stage |
| Action acceptance rate | ≥ 50% |
| False-alarm rate (disease) | ≤ 10% |
| Farmer yield improvement | +5–10% (band-reported) |
| Input reduction (N/water) | 5–15% |
| Explanation helpfulness score | ≥ 4/5 |
| Data completeness | ≥ 70% fields compliant |

## 🌍 Regional Focus

### Zimbabwe (maize, groundnut)
- Focus: rain-aligned N timing & drought awareness
- Goal: +5–10% yield band increase with low-input operations

### Poland (wheat, potato)
- Focus: optimized N split & disease timing compliance
- Goal: maintain yield with ≤15% input reduction

## 🔧 Integration with API Gateway

The CIE is designed to integrate with the PreciAgro API Gateway. Wire this service behind your gateway as `/engines/cie/*`:

```python
# In your API Gateway
from preciagro.packages.engines.crop_intelligence.app.main import app as cie_app

gateway.mount("/engines/cie", cie_app)
```

## 🔮 Future Enhancements

### Next Sprint
- Replace water heuristics with FAO-56 ETc calculations
- Implement multi-armed bandit for N timing optimization
- Add model registry hooks for ML integration
- Replace in-memory storage with Postgres/Redis
- Add authentication and rate limiting

### Phase II
- GDD-based phenology tracking
- Integration with satellite imagery services
- Advanced disease models with leaf wetness sensors
- Prescription maps for variable rate application
- Mobile app integration

## 📝 Development Notes

### Service Architecture
- **Stateless design**: All state stored in repos (currently in-memory)
- **Event-driven**: All actions emit events for PIE learning loop
- **Explainable**: Every recommendation includes reasoning
- **Modular**: Services can be swapped independently

### Adding New Features
1. Add new service in `app/services/`
2. Import and use in `app/api/router.py`
3. Add tests in tests
4. Update this README

### Configuration
Edit `app/core/config.py` to modify:
- External service URLs
- Feature flags
- Environment settings

## 🤝 Contributing

When adding features:
1. Maintain 100% explainability
2. Add comprehensive docstrings
3. Include unit tests
4. Update API documentation
5. Log events for learning hooks

## 📄 License

Part of the PreciAgro MVP project.

## 📧 Contact

For questions or support, contact the PreciAgro development team.

---

**Version**: 0.1.0  
**Status**: MVP - Production Lean  
**Last Updated**: October 2025

```

You can now copy this entire README content and paste it into your file manually!You can now copy this entire README content and paste it into your file manually!
```