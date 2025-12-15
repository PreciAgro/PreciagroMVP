# Technical Debt Register

This document tracks known technical debt in the PreciagroMVP codebase.

## High Priority 🔴

### 1. Event Rule Evaluation Trigger
**Location**: `preciagro/packages/engines/temporal_logic/api/routes/events.py:405`

```python
# TODO: Trigger rule evaluation and compilation for this event
```

**Issue**: Events are created but not automatically triggering rule evaluation  
**Impact**: Rules may not execute as expected  
**Effort**: Medium (2-3 days)  
**Recommendation**: Implement event-driven rule evaluation pipeline

---

## Medium Priority 🟡

### 2. Inventory Backend Implementation
**Location**: `preciagro/packages/engines/inventory/__init__.py`

**Lines 20, 83**:
- TODO: Implement concrete backends (database, file system)
- TODO: Replace hardcoded logic with actual inventory queries

**Issue**: Using stub/mock inventory data  
**Impact**: Inventory features not functional  
**Effort**: High (1-2 weeks)  
**Recommendation**: Implement PostgreSQL-backed inventory system

---

### 3. Image Analysis Model Integration
**Location**: `preciagro/packages/engines/image_analysis/__init__.py:27`

```python
# TODO: Replace heuristic with actual model inference
```

**Issue**: Using heuristic rules instead of ML model  
**Impact**: Lower accuracy for image classification  
**Effort**: High (2-3 weeks)  
**Recommendation**: Integrate trained TensorFlow/PyTorch model

---

### 4. Crop Intelligence Ranker Integration
**Location**: `preciagro/packages/engines/crop_intelligence/tests/test_quick_qa.py:237`

```python
# TODO: Implement ranker integration
```

**Issue**: Missing ranking logic for QA results  
**Impact**: Results may not be optimally ordered  
**Effort**: Medium (3-5 days)  
**Recommendation**: Implement result ranking algorithm

---

## Low Priority 🟢

### 5. Time Constraint Handling
**Location**: `preciagro/packages/engines/temporal_logic/dispatcher_minimal.py:383`

```python
# TODO: Handle start_at_local and end_at_local time constraints
```

**Issue**: Local time constraints not fully implemented  
**Impact**: Limited scheduling flexibility  
**Effort**: Low (1-2 days)  
**Recommendation**: Add timezone-aware scheduling

---

### 6. Data Normalization Enhancements
**Location**: `preciagro/packages/engines/data_integration/pipeline/normalize_openweather.py`

**Lines 14, 44**:
- TODO: Handle millisecond timestamps for other providers
- TODO: Enhance normalization logic

**Issue**: Limited provider support and edge cases  
**Impact**: May fail with non-OpenWeather data  
**Effort**: Medium (3-5 days)  
**Recommendation**: Generalize normalization pipeline

---

### 7. Connector Future Work
**Location**: `preciagro/packages/engines/data_integration/connectors/`

Multiple TODOs in:
- `base.py:14` - Connector framework enhancements
- `http_json.py:16` - HTTP connector improvements
- `openweather.py:20` - OpenWeather-specific enhancements

**Issue**: Connector framework could be more robust  
**Impact**: Limited to current use cases  
**Effort**: Medium (1 week)  
**Recommendation**: Implement when adding new data sources

---

## Summary

| Priority | Count | Total Effort |
|----------|-------|--------------|
| High 🔴 | 1 | 2-3 days |
| Medium 🟡 | 3 | 4-6 weeks |
| Low 🟢 | 3 | 2-3 weeks |
| **Total** | **7** | **~8 weeks** |

## Resolution Strategy

1. **Immediate**: Fix high-priority item (event rule evaluation)
2. **Q1 2024**: Address medium-priority items based on feature priorities
3. **Q2 2024**: Clean up low-priority items as time permits
4. **Ongoing**: Review and update quarterly

## Notes

- No FIXME comments found (good sign!)
- Most TODOs are feature enhancements, not bugs
- Technical debt is well-documented in code
- Prioritize based on user impact and dependencies
