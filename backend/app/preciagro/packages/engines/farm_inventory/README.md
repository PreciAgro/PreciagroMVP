# Farm Inventory Engine

**Decision Constraint Engine for Farm Inputs**

The Farm Inventory Engine is the **economic and operational ground truth** of the farm. It tracks, validates, predicts, and reasons over farm inputs so that:

- No recommendation is made if required inputs do not exist
- Farmers understand what they have, what they are using, and what they will run out of
- The system prevents waste, shortages, and unrealistic advice

## Core Responsibilities

1. **Track Inventory**: Seeds, fertilizers, chemicals, animal feed, tools and equipment
2. **Track Usage Events**: Manual farmer input and automated deduction from scheduled/recommended actions
3. **Predict Depletion**: Estimate when inputs will run out based on crop type, growth stage, field size, and agronomic rules
4. **Validate Actions**: Before any recommendation or scheduled task executes, confirm inventory availability
5. **Generate Alerts**: Low stock, critical shortages, expiry or spoilage risk
6. **Provide Economic Context**: Cost already invested and estimated remaining input cost until harvest
7. **Offline-First Operation**: Local storage with sync to central server when connectivity is restored

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Farm Inventory Engine                     │
├─────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                         │
│  ├─ Inventory Management                                     │
│  ├─ Usage Logging                                            │
│  ├─ Action Validation                                        │
│  ├─ Alerts & Notifications                                   │
│  └─ Economic Context                                         │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                               │
│  ├─ DepletionPredictor (rule-based estimation)             │
│  ├─ ActionValidator (inventory availability checks)         │
│  ├─ AlertGenerator (low stock, expiry, critical)            │
│  └─ EconomicContextService (cost calculations)              │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer                                            │
│  ├─ InventoryRepository                                      │
│  ├─ UsageLogRepository (never deleted)                       │
│  └─ AlertRepository                                          │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  ├─ InventoryItem                                            │
│  ├─ UsageLog                                                │
│  ├─ InventoryAlert                                           │
│  └─ SyncState (offline-first)                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Models

### InventoryItem
- Tracks all farm inputs (seeds, fertilizers, chemicals, feed, tools)
- Includes quantity, unit, cost, expiry dates, batch tracking
- Supports metadata for extensibility

### UsageLog
- **Never deleted** - full audit trail
- Records every inventory deduction
- Links to fields, crop stages, usage reasons

### InventoryAlert
- Low stock warnings
- Critical shortage alerts
- Expiry notifications
- Depletion predictions

## API Endpoints

### Inventory Management
- `POST /inventory/items` - Add inventory item
- `GET /inventory/items/{item_id}` - Get item details
- `GET /inventory/items` - List items (filtered by farmer, category)
- `PATCH /inventory/items/{item_id}` - Update item
- `DELETE /inventory/items/{item_id}` - Soft delete item

### Usage Tracking
- `POST /inventory/usage` - Record usage (automatically deducts inventory)
- `GET /inventory/usage` - List usage logs

### Validation
- `POST /inventory/validate` - **Validate action against inventory** (MUST be called before recommendations)
- `GET /inventory/status` - Get inventory status with depletion predictions

### Alerts
- `GET /inventory/alerts` - Get alerts for farmer
- `POST /inventory/alerts/{alert_id}/resolve` - Resolve alert

### Analytics
- `GET /inventory/predict/{item_id}` - Predict depletion
- `GET /inventory/economic-context` - Economic context (invested cost, remaining cost)
- `GET /inventory/summary` - Inventory summary

## Integration with Other Engines

### Crop Intelligence Engine
- Get crop type and growth stage for better depletion predictions
- Retrieve agronomic rules for usage rate calculations

### Temporal Logic Engine
- Validate scheduled tasks against inventory
- Notify when inventory is deducted for scheduled tasks

### Diagnosis & Recommendation Engine
- **MUST call `/inventory/validate` before executing any recommendation**
- Block or modify recommendations if inventory is unavailable

### AgroLLM Engine
- Provide inventory context in explanations
- Include economic context in summaries

## Depletion Prediction Logic

Rule-based estimation (MVP):
```
remaining_days = current_quantity / estimated_daily_usage
```

Estimated daily usage is derived from:
- Historical usage logs (last N days)
- Crop type and growth stage (from Crop Intelligence Engine)
- Field size
- Agronomic rules

**Note**: Machine learning is explicitly out of scope for MVP.

## Offline-First Support

- **Local Storage**: SQLite for offline usage
- **Server Sync**: PostgreSQL for centralized storage
- **Conflict Resolution**: Server state is authoritative
- **Sync State Tracking**: All conflicts logged for audit

## Security & Auditability

- Role-based access control (via Security & Access Engine)
- Encrypted storage and transit
- Full audit trail (usage logs never deleted)
- All inventory changes tracked with timestamps

## Configuration

Environment variables:
```bash
# Database
DATABASE_URL=sqlite:///./farm_inventory.db  # or postgresql://...
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Authentication
API_AUTH_TOKEN=your-token-here

# Offline-first
OFFLINE_MODE=false
SYNC_ENABLED=true
SYNC_INTERVAL_SECONDS=300

# External services
CROP_INTELLIGENCE_URL=http://localhost:8104
TEMPORAL_LOGIC_URL=http://localhost:8100

# Alert thresholds
LOW_STOCK_THRESHOLD=0.2  # 20% of typical usage
CRITICAL_STOCK_THRESHOLD=0.1  # 10% of typical usage
EXPIRY_WARNING_DAYS=30
```

## Usage Example

### 1. Add Inventory Item
```python
POST /inventory/items
{
  "farmer_id": "farmer-123",
  "category": "fertilizer",
  "name": "NPK 15-15-15",
  "quantity": 100.0,
  "unit": "kg",
  "cost_per_unit": 2.50,
  "purchase_date": "2024-01-15"
}
```

### 2. Validate Action Before Execution
```python
POST /inventory/validate
{
  "farmer_id": "farmer-123",
  "field_id": "field-456",
  "required_items": [
    {
      "item_id": "item-789",
      "quantity": 10.0,
      "unit": "kg"
    }
  ]
}
```

### 3. Record Usage (Automatically Deducts)
```python
POST /inventory/usage
{
  "item_id": "item-789",
  "farmer_id": "farmer-123",
  "field_id": "field-456",
  "quantity_used": 10.0,
  "usage_reason": "recommendation"
}
```

## Edge Cases Handled

- ✅ Partial usage
- ✅ Shared inventory across fields
- ✅ Manual corrections
- ✅ Expired inputs
- ✅ Emergency usage
- ✅ Prevention of negative inventory

## MVP Acceptance Criteria

The engine is considered complete when:

- ✅ All recommendations are inventory-validated
- ✅ Farmers can clearly see current stock and future shortages
- ✅ Usage logs exist for every deduction
- ✅ Offline usage works reliably
- ✅ No negative inventory states are possible

## Strategic Note

This engine must not be presented as "inventory management".

It is the **decision constraint engine** that ensures all AI advice is realistic, affordable, and executable.

Built with production discipline. This engine will power future optimization, automation, and monetization layers.

