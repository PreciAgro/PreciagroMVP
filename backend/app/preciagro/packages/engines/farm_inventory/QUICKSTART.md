# Farm Inventory Engine - Quick Start Guide

## Running the Engine

### 1. Set Environment Variables

```bash
# Database (SQLite for development, PostgreSQL for production)
export DATABASE_URL="sqlite:///./farm_inventory.db"

# Authentication
export API_AUTH_TOKEN="your-secret-token"

# External services (optional)
export CROP_INTELLIGENCE_URL="http://localhost:8104"
export TEMPORAL_LOGIC_URL="http://localhost:8100"
```

### 2. Run Database Migrations

```bash
# Set DATABASE_URL for migrations
export DATABASE_URL="sqlite:///./farm_inventory.db"

# Run Alembic migration
alembic upgrade head
```

### 3. Start the Server

```bash
# Using uvicorn
uvicorn preciagro.packages.engines.farm_inventory.app.main:app --port 8105

# Or using the FastAPI app directly
python -m preciagro.packages.engines.farm_inventory.app.main
```

The engine will be available at `http://localhost:8105`

## Quick API Examples

### Add Inventory Item

```bash
curl -X POST http://localhost:8105/inventory/items \
  -H "Content-Type: application/json" \
  -H "X-PreciAgro-Token: your-secret-token" \
  -d '{
    "farmer_id": "farmer-123",
    "category": "fertilizer",
    "name": "NPK 15-15-15",
    "quantity": 100.0,
    "unit": "kg",
    "cost_per_unit": 2.50,
    "purchase_date": "2024-01-15"
  }'
```

### Validate Action (Before Recommendation)

```bash
curl -X POST http://localhost:8105/inventory/validate \
  -H "Content-Type: application/json" \
  -H "X-PreciAgro-Token: your-secret-token" \
  -d '{
    "farmer_id": "farmer-123",
    "field_id": "field-456",
    "required_items": [
      {
        "item_id": "item-uuid-here",
        "quantity": 10.0,
        "unit": "kg"
      }
    ]
  }'
```

### Record Usage (Automatically Deducts)

```bash
curl -X POST http://localhost:8105/inventory/usage \
  -H "Content-Type: application/json" \
  -H "X-PreciAgro-Token: your-secret-token" \
  -d '{
    "item_id": "item-uuid-here",
    "farmer_id": "farmer-123",
    "field_id": "field-456",
    "quantity_used": 10.0,
    "usage_reason": "recommendation"
  }'
```

### Get Inventory Status

```bash
curl "http://localhost:8105/inventory/status?farmer_id=farmer-123" \
  -H "X-PreciAgro-Token: your-secret-token"
```

### Get Alerts

```bash
curl "http://localhost:8105/inventory/alerts?farmer_id=farmer-123" \
  -H "X-PreciAgro-Token: your-secret-token"
```

### Predict Depletion

```bash
curl "http://localhost:8105/inventory/predict/item-uuid-here?lookback_days=7" \
  -H "X-PreciAgro-Token: your-secret-token"
```

## Integration with Other Engines

### From Diagnosis & Recommendation Engine

**CRITICAL**: Always validate before executing recommendations:

```python
import httpx

async def execute_recommendation(recommendation_id: str, required_items: list):
    # Step 1: Validate inventory
    async with httpx.AsyncClient() as client:
        validation = await client.post(
            "http://localhost:8105/inventory/validate",
            json={
                "farmer_id": farmer_id,
                "required_items": required_items
            },
            headers={"X-PreciAgro-Token": API_TOKEN}
        )
        
        if not validation.json()["is_valid"]:
            # Block or modify recommendation
            missing = validation.json()["missing_items"]
            raise InsufficientInventoryError(missing)
    
    # Step 2: Execute recommendation
    # ... execute action ...
    
    # Step 3: Record usage
    await client.post(
        "http://localhost:8105/inventory/usage",
        json={
            "item_id": item_id,
            "farmer_id": farmer_id,
            "quantity_used": quantity,
            "usage_reason": "recommendation"
        },
        headers={"X-PreciAgro-Token": API_TOKEN}
    )
```

### From Temporal Logic Engine

When a scheduled task requires inventory:

```python
# Before executing scheduled task
validation = await inventory_client.validate_action({
    "farmer_id": farmer_id,
    "required_items": task.required_items
})

if not validation["is_valid"]:
    # Reschedule or cancel task
    await temporal_client.cancel_task(task_id)
```

## Key Features

✅ **No Negative Inventory**: All deductions are validated before execution  
✅ **Full Audit Trail**: Usage logs are never deleted  
✅ **Depletion Prediction**: Rule-based estimation of when items will run out  
✅ **Automatic Alerts**: Low stock, critical, and expiry warnings  
✅ **Economic Context**: Track invested costs and estimate remaining costs  
✅ **Offline-First**: SQLite for local, PostgreSQL for server sync  

## Testing

```bash
# Health check
curl http://localhost:8105/health

# Root endpoint
curl http://localhost:8105/
```

## Production Deployment

1. Use PostgreSQL instead of SQLite
2. Set strong `API_AUTH_TOKEN`
3. Configure external service URLs
4. Enable Prometheus metrics (default: enabled)
5. Set up database connection pooling
6. Configure sync for offline-first mode

