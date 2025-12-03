# Crop Intelligence Engine - Completion Guide

## Executive Summary

The Crop Intelligence Engine (CIE) is **~75% complete**. The core architecture, API endpoints, and database schema are in place, but several critical components need implementation or enhancement to reach production readiness.

**Estimated Completion Time**: 4-6 weeks with 1-2 engineers

---

## Current Status

### ✅ What's Complete

1. **API Endpoints** - All 10 endpoints are implemented and functional
2. **Database Schema** - Complete with Alembic migrations
3. **Core Services** - Most service classes exist with basic implementations
4. **Model Registry** - Infrastructure for ML model management
5. **Integration Hub** - Connectors to other engines (GeoContext, Temporal Logic, etc.)
6. **Event Logging** - Learning hooks for feedback collection
7. **Physics-Based Calculations** - FAO-56 water calculations exist in `water_physics.py`
8. **Test Infrastructure** - Test framework in place (though some tests are skipped)

### ⚠️ What's Incomplete

1. **ML Model Artifacts** - Models referenced but may not exist on disk
2. **Water Management Integration** - FAO-56 exists but not fully integrated
3. **Budget Constraints** - Action filtering by budget not implemented
4. **Decision Ranker** - Basic implementation, needs enhancement
5. **Disease Risk Assessment** - Very basic, needs expansion
6. **GDD Calculations** - Growing Degree Days not fully implemented
7. **Test Coverage** - Several tests are skipped/pending

---

## Critical Tasks to Complete

### 🔴 Priority 1: Core Functionality (Weeks 1-2)

#### 1.1 Integrate FAO-56 Water Management

**Current State**: `water_physics.py` has full FAO-56 implementation, but `phenology_water.py` still uses placeholder logic.

**Tasks**:
- [ ] Replace placeholder in `phenology_water.py` with calls to `water_physics.py`
- [ ] Integrate water balance calculations into `field_state_tracker.py`
- [ ] Add irrigation recommendations based on water deficit
- [ ] Update action recommender to include water management actions

**Files to Modify**:
- `app/services/phenology_water.py` - Replace placeholder (line 19)
- `app/services/field_state_tracker.py` - Add water balance tracking
- `app/services/action_recommender.py` - Add irrigation actions

**Example Integration**:
```python
# In phenology_water.py
from ..core.water_physics import (
    run_soil_water_bucket,
    estimate_irrigation_need,
    get_water_stress_level,
    WeatherDay,
    SoilBucket
)

def water_need_message(self, whc_mm: Optional[float], rain_forecast_mm: Optional[float], 
                       weather_history: List[WeatherDay], crop: str, planting_date: date) -> dict:
    if whc_mm is None:
        return {"note": "insufficient soil data"}
    
    soil_bucket = SoilBucket(whc_mm=whc_mm, current_mm=whc_mm * 0.7)
    water_balance = run_soil_water_bucket(weather_history, soil_bucket, crop, planting_date)
    
    mm_needed, timing, confidence = estimate_irrigation_need(water_balance, rain_forecast_mm or 0)
    latest = water_balance[-1] if water_balance else None
    
    if latest:
        stress_level, urgency, recommendation = get_water_stress_level(
            latest.soil_mm, whc_mm, crop_stage
        )
        return {
            "irrigation_mm": mm_needed,
            "timing": timing,
            "stress_level": stress_level,
            "urgency": urgency,
            "recommendation": recommendation,
            "confidence": confidence
        }
    return {"note": "insufficient weather history"}
```

#### 1.2 Implement GDD (Growing Degree Days) Calculations

**Current State**: GDD mentioned in model inputs but calculation not implemented.

**Tasks**:
- [ ] Create `app/core/gdd_calculator.py` with GDD calculation functions
- [ ] Integrate GDD into growth stage estimation
- [ ] Add GDD tracking to telemetry repository
- [ ] Update field state to include cumulative GDD

**Implementation**:
```python
# app/core/gdd_calculator.py
def calculate_gdd(tmax_c: float, tmin_c: float, base_temp: float = 10.0, 
                  max_temp: float = 30.0) -> float:
    """Calculate Growing Degree Days for a single day."""
    tmean = (tmax_c + tmin_c) / 2.0
    tmean = max(base_temp, min(tmean, max_temp))
    return max(0.0, tmean - base_temp)

def cumulative_gdd(weather_history: List[WeatherDay], base_temp: float = 10.0) -> float:
    """Calculate cumulative GDD from planting date."""
    return sum(calculate_gdd(w.tmax_c, w.tmin_c, base_temp) for w in weather_history)
```

#### 1.3 Enhance Growth Stage Estimation

**Current State**: Basic heuristic fallback exists, but needs GDD integration.

**Tasks**:
- [ ] Integrate GDD into `growth_stage_estimator.py`
- [ ] Improve heuristic fallback with GDD + NDVI combination
- [ ] Add stage confidence based on data quality
- [ ] Support crop-specific GDD thresholds

**Files to Modify**:
- `app/services/growth_stage_estimator.py` - Add GDD features
- `app/services/field_state_tracker.py` - Include GDD in state

#### 1.4 Expand Disease Risk Assessment

**Current State**: Only basic late blight check exists.

**Tasks**:
- [ ] Expand `health_risk.py` to support multiple diseases
- [ ] Integrate with `disease_physics.py` (already exists in core)
- [ ] Add crop-specific disease models
- [ ] Include pest risk assessment

**Diseases to Add**:
- Maize: Gray leaf spot, Northern corn leaf blight, Rust
- Wheat: Powdery mildew, Septoria, Rust
- Potato: Early blight, Late blight (enhance existing)

**Files to Modify**:
- `app/services/health_risk.py` - Expand disease_cards method
- `app/core/disease_physics.py` - May need enhancement

---

### 🟡 Priority 2: ML Model Integration (Weeks 2-3)

#### 2.1 Verify/Obtain ML Model Artifacts

**Current State**: Models referenced in `config/models.json` but artifacts may not exist.

**Required Models**:
1. `crop_stage_detector` - `models/stage_detector_v0.1.0.pkl`
2. `yield_estimator_maize` - `models/yield_maize_v0.2.1.xgb`
3. `nitrogen_timing_optimizer` - `models/n_timing_bandit_v0.1.0.pkl`

**Tasks**:
- [ ] Verify model files exist in `preciagro/packages/engines/crop_intelligence/models/`
- [ ] If missing, either:
  - Train models using pilot data
  - Use placeholder/stub models for development
  - Download from model registry if available
- [ ] Validate model file checksums match `models.json`
- [ ] Test model loading and inference
- [ ] Add model validation tests

**Model Training (if needed)**:
```python
# Example training script structure
# scripts/train_stage_detector.py
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import joblib

# Load training data
df = pd.read_csv("data/training/stage_labels.csv")
X = df[['ndvi_avg', 'ndvi_std', 'days_since', 'gdd_cumulative']]
y = df['stage']

# Train model
model = RandomForestClassifier(n_estimators=100, max_depth=10)
model.fit(X, y)

# Save
joblib.dump(model, "models/stage_detector_v0.1.0.pkl")
```

#### 2.2 Implement Budget-Based Action Filtering

**Current State**: `decision_ranker.py` exists but budget filtering not implemented (test skipped).

**Tasks**:
- [ ] Add budget constraints to `ActionContext`
- [ ] Implement cost estimation for actions
- [ ] Filter/rank actions by budget in `decision_ranker.py`
- [ ] Add budget class mapping (low/medium/high)
- [ ] Update action recommender to respect budget

**Implementation**:
```python
# In decision_ranker.py
def rank(self, field_id: str, candidates: List[ActionOut], 
         budget_class: str = "medium") -> List[ActionOut]:
    # Cost mapping
    cost_map = {
        "N_Topdress": {"low": 50, "medium": 100, "high": 150},
        "Fungicide": {"low": 30, "medium": 60, "high": 90},
        "Irrigation": {"low": 20, "medium": 40, "high": 80},
    }
    
    # Filter by budget
    budget_limit = {"low": 100, "medium": 300, "high": 1000}[budget_class]
    filtered = []
    total_cost = 0
    
    for action in sorted(candidates, key=lambda a: a.impact_score, reverse=True):
        cost = cost_map.get(action.action, {}).get(budget_class, 0)
        if total_cost + cost <= budget_limit:
            filtered.append(action)
            total_cost += cost
        if len(filtered) >= 3:  # Top 3 actions
            break
    
    return filtered
```

#### 2.3 Enhance Decision Ranker

**Current State**: Basic sorting by impact score only.

**Tasks**:
- [ ] Add multi-factor ranking (impact, urgency, cost-effectiveness)
- [ ] Implement contextual bandit for N timing (if model available)
- [ ] Add action conflict detection (e.g., don't recommend irrigation + fungicide same day)
- [ ] Consider farmer feedback history in ranking

---

### 🟢 Priority 3: Testing & Quality (Weeks 3-4)

#### 3.1 Complete Test Suite

**Current State**: Several tests are skipped.

**Tasks**:
- [ ] Implement `test_budget_constraints` tests
- [ ] Complete `test_edge_cases` tests
- [ ] Add integration tests for full action pipeline
- [ ] Add tests for water management integration
- [ ] Add tests for GDD calculations
- [ ] Add model loading/inference tests

**Files to Complete**:
- `tests/test_quick_qa.py` - Unskip and implement pending tests
- `tests/test_integration.py` - Create new integration test file

#### 3.2 Add Model Validation Tests

**Tasks**:
- [ ] Test model loading with missing files (should fallback gracefully)
- [ ] Test model inference with valid/invalid inputs
- [ ] Test model versioning and rollback
- [ ] Test model metadata validation

#### 3.3 Improve Error Handling

**Tasks**:
- [ ] Add proper error handling for model loading failures
- [ ] Add validation for telemetry data quality
- [ ] Add graceful degradation when models unavailable
- [ ] Improve error messages for API consumers

---

### 🔵 Priority 4: Integration & Polish (Weeks 4-5)

#### 4.1 Enhance Integration with Other Engines

**Current State**: Integration hub exists but may need enhancement.

**Tasks**:
- [ ] Verify GeoContext integration for soil/climate data
- [ ] Verify Temporal Logic integration for scheduling
- [ ] Add error handling for engine failures
- [ ] Add caching for external engine responses
- [ ] Add fallback when engines unavailable

#### 4.2 Improve Explanations

**Current State**: Basic explanation service exists.

**Tasks**:
- [ ] Enhance explanation quality and detail
- [ ] Add crop-specific explanations
- [ ] Include uncertainty quantification in explanations
- [ ] Add visual aids (charts, graphs) where applicable

#### 4.3 Add Monitoring & Observability

**Tasks**:
- [ ] Add Prometheus metrics for:
  - Action recommendation counts
  - Model inference latency
  - Water balance calculations
  - Disease risk assessments
- [ ] Add structured logging for key events
- [ ] Add performance tracking for model calls

#### 4.4 Documentation

**Tasks**:
- [ ] Update README with completion status
- [ ] Document model training process
- [ ] Create API usage examples
- [ ] Document configuration options
- [ ] Create troubleshooting guide

---

## Model Artifacts Required

### Current Model Requirements

Based on `config/models.json`, the following models are expected:

1. **crop_stage_detector** (v0.1.0)
   - Type: sklearn RandomForestClassifier
   - File: `models/stage_detector_v0.1.0.pkl`
   - Size: ~2.4 MB
   - Status: **Check if exists**

2. **yield_estimator_maize** (v0.2.1)
   - Type: XGBoost regressor
   - File: `models/yield_maize_v0.2.1.xgb`
   - Size: ~1.8 MB
   - Status: **Check if exists**

3. **nitrogen_timing_optimizer** (v0.1.0)
   - Type: Thompson Sampling bandit
   - File: `models/n_timing_bandit_v0.1.0.pkl`
   - Size: ~0.3 MB
   - Status: **Check if exists**

### Action Plan for Missing Models

**Option 1: Use Stub Models (Development)**
- Create simple stub models that return reasonable defaults
- Allows development to continue without real models
- Models can be replaced later

**Option 2: Train Models (Production)**
- Collect training data from pilot deployments
- Train models using scripts in `data/export_datasets.py`
- Validate models meet accuracy targets
- Deploy models following versioning in `models.json`

**Option 3: Use Pre-trained Models (If Available)**
- Check if models exist in external model registry
- Download and validate checksums
- Deploy to production

---

## Database & Storage

### Current State
- ✅ Database schema complete
- ✅ Alembic migrations exist
- ✅ Repositories implemented

### Tasks
- [ ] Verify database migrations run successfully
- [ ] Test data persistence and retrieval
- [ ] Add database indexes for performance
- [ ] Add data retention policies
- [ ] Test database connection pooling

---

## Configuration & Environment

### Required Environment Variables

Document all required environment variables:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/preciagro

# API Auth
API_AUTH_TOKEN=your-token-here

# Feature Flags
ENABLE_BANDIT_N_TIMING=false
ENABLE_FAO56_WATER=true

# Model Paths (if custom)
MODEL_ARTIFACT_ROOT=/path/to/models

# External Services
GEO_CONTEXT_URL=http://localhost:8102
TEMPORAL_LOGIC_URL=http://localhost:8100
```

### Tasks
- [ ] Create `.env.example` file
- [ ] Document all configuration options
- [ ] Add configuration validation on startup
- [ ] Add feature flag documentation

---

## Testing Checklist

### Unit Tests
- [ ] Growth stage estimator (with/without models)
- [ ] Water management calculations
- [ ] GDD calculations
- [ ] Disease risk assessment
- [ ] Nutrient timing logic
- [ ] Yield prediction (with/without models)
- [ ] Decision ranker
- [ ] Budget filtering

### Integration Tests
- [ ] Full action recommendation pipeline
- [ ] Field registration → telemetry → state → actions
- [ ] Model loading and inference
- [ ] External engine integration
- [ ] Database persistence

### End-to-End Tests
- [ ] Complete farmer workflow (register → telemetry → get actions → feedback)
- [ ] Multi-field scenarios
- [ ] Error handling and fallbacks
- [ ] Performance under load

---

## Performance Targets

Based on MVP goals:

| Metric | Target | Current Status |
|--------|--------|----------------|
| Stage accuracy | ≥80% within ±1 stage | ⚠️ Needs validation |
| Action acceptance rate | ≥50% | ⚠️ Needs tracking |
| False-alarm rate (disease) | ≤10% | ⚠️ Needs validation |
| API latency (p95) | <200ms | ✅ Likely met |
| Model inference latency | <100ms | ⚠️ Needs measurement |

---

## Deployment Readiness

### Pre-Deployment Checklist

- [ ] All critical tasks completed
- [ ] Test coverage >80%
- [ ] Models validated and deployed
- [ ] Database migrations tested
- [ ] Configuration documented
- [ ] Monitoring in place
- [ ] Error handling robust
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] Security review passed

---

## Estimated Timeline

### Week 1-2: Core Functionality
- Integrate FAO-56 water management
- Implement GDD calculations
- Enhance growth stage estimation
- Expand disease risk assessment

### Week 2-3: ML Integration
- Verify/obtain model artifacts
- Implement budget filtering
- Enhance decision ranker
- Test model inference

### Week 3-4: Testing
- Complete test suite
- Add integration tests
- Improve error handling
- Performance testing

### Week 4-5: Polish
- Enhance integrations
- Improve explanations
- Add monitoring
- Complete documentation

### Week 5-6: Buffer & Deployment
- Bug fixes
- Performance optimization
- Final testing
- Deployment preparation

---

## Risk Mitigation

### High-Risk Areas

1. **Missing ML Models**
   - **Risk**: Models don't exist, blocking production
   - **Mitigation**: Create stub models for development, plan model training

2. **Model Accuracy**
   - **Risk**: Models don't meet accuracy targets
   - **Mitigation**: Validate models before deployment, have fallback heuristics

3. **Integration Failures**
   - **Risk**: External engines unavailable
   - **Mitigation**: Implement graceful degradation, caching, fallbacks

4. **Performance Issues**
   - **Risk**: Slow API responses
   - **Mitigation**: Profile and optimize, add caching, consider async improvements

---

## Success Criteria

The Crop Intelligence Engine is considered **complete** when:

1. ✅ All 10 API endpoints functional and tested
2. ✅ Water management uses FAO-56 calculations
3. ✅ GDD calculations integrated
4. ✅ Disease risk assessment supports multiple diseases
5. ✅ ML models loaded and inference working (or graceful fallback)
6. ✅ Budget filtering implemented
7. ✅ Test coverage >80%
8. ✅ Performance targets met
9. ✅ Documentation complete
10. ✅ Ready for pilot deployment

---

## Next Steps

1. **Immediate**: Review this guide and prioritize tasks
2. **Week 1**: Start with Priority 1 tasks (core functionality)
3. **Week 2**: Begin ML model verification/integration
4. **Ongoing**: Regular testing and validation
5. **Final**: Deployment preparation and documentation

---

## Resources

- **Model Registry**: `config/models.json`
- **API Documentation**: `README.md`
- **Test Suite**: `tests/`
- **Physics Calculations**: `app/core/water_physics.py`, `app/core/disease_physics.py`
- **Service Implementations**: `app/services/`
- **Database Models**: `app/db/models.py`

---

**Last Updated**: Based on codebase analysis as of current date
**Status**: ~75% Complete - 4-6 weeks to production ready

