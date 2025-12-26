"""API routes for Farm Inventory Engine."""

from __future__ import annotations

from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session

from ..db import get_session
from ..models.schemas import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemOut,
    UsageLogCreate,
    UsageLogOut,
    ActionValidationRequest,
    ActionValidationResponse,
    InventoryStatusResponse,
    LowStockAlertResponse,
    DepletionPredictionResponse,
    EconomicContextResponse,
    InventorySummaryResponse,
    InventoryCategory,
)
from ..repos import InventoryRepository, UsageLogRepository, AlertRepository
from ..services import (
    DepletionPredictor,
    ActionValidator,
    AlertGenerator,
    EconomicContextService,
)
from ..security.deps import require_service_token, SecurityContext

router = APIRouter(
    prefix="/inventory",
    tags=["Farm Inventory"],
    dependencies=[Depends(require_service_token)],
)


# Inventory Item Management
@router.post("/items", response_model=InventoryItemOut, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    item_data: InventoryItemCreate,
    db: Session = Depends(get_session),
) -> InventoryItemOut:
    """Add a new inventory item."""
    repo = InventoryRepository(db)
    item = repo.create(item_data)
    return InventoryItemOut.model_validate(item)


@router.get("/items/{item_id}", response_model=InventoryItemOut)
def get_inventory_item(
    item_id: str,
    db: Session = Depends(get_session),
) -> InventoryItemOut:
    """Get inventory item by ID."""
    repo = InventoryRepository(db)
    item = repo.get_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item {item_id} not found",
        )
    return InventoryItemOut.model_validate(item)


@router.get("/items", response_model=List[InventoryItemOut])
def list_inventory_items(
    farmer_id: str = Query(..., description="Farmer identifier"),
    category: Optional[InventoryCategory] = Query(None, description="Filter by category"),
    include_zero: bool = Query(False, description="Include items with zero quantity"),
    db: Session = Depends(get_session),
) -> List[InventoryItemOut]:
    """List inventory items for a farmer."""
    repo = InventoryRepository(db)
    items = repo.get_by_farmer(
        farmer_id=farmer_id,
        category=category.value if category else None,
        include_zero=include_zero,
    )
    return [InventoryItemOut.model_validate(item) for item in items]


@router.patch("/items/{item_id}", response_model=InventoryItemOut)
def update_inventory_item(
    item_id: str,
    update_data: InventoryItemUpdate,
    db: Session = Depends(get_session),
) -> InventoryItemOut:
    """Update an inventory item."""
    repo = InventoryRepository(db)
    item = repo.update(item_id, update_data)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item {item_id} not found",
        )
    return InventoryItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: str,
    db: Session = Depends(get_session),
) -> None:
    """Delete an inventory item (soft delete)."""
    repo = InventoryRepository(db)
    success = repo.delete(item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item {item_id} not found",
        )


# Usage Log Management
@router.post("/usage", response_model=UsageLogOut, status_code=status.HTTP_201_CREATED)
def record_usage(
    usage_data: UsageLogCreate,
    db: Session = Depends(get_session),
    security: SecurityContext = Depends(require_service_token),
) -> UsageLogOut:
    """Record inventory usage (deducts from inventory).

    Automatically sets source_engine from security context if not provided.
    """
    inventory_repo = InventoryRepository(db)
    usage_repo = UsageLogRepository(db)

    # Auto-populate source_engine from security context if not provided
    if not usage_data.source_engine and security.engine_name:
        usage_data.source_engine = security.engine_name

    # Check if item exists and has sufficient quantity
    item = inventory_repo.get_by_id(usage_data.item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item {usage_data.item_id} not found",
        )

    if item.quantity < usage_data.quantity_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock. Available: {item.quantity} {item.unit}, "
                f"Required: {usage_data.quantity_used} {item.unit}"
            ),
        )

    # Deduct from inventory (with transaction locking)
    updated_item = inventory_repo.deduct_quantity(
        usage_data.item_id, usage_data.quantity_used, allow_negative=False
    )
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to deduct inventory",
        )

    # Create usage log (with source_engine and action_id for debugging)
    usage_log = usage_repo.create(usage_data)

    # Generate alerts if needed
    alert_gen = AlertGenerator(inventory_repo, AlertRepository(db), usage_repo)
    alert_gen.generate_alerts_for_farmer(usage_data.farmer_id)

    return UsageLogOut.model_validate(usage_log)


@router.get("/usage", response_model=List[UsageLogOut])
def list_usage_logs(
    farmer_id: str = Query(..., description="Farmer identifier"),
    item_id: Optional[str] = Query(None, description="Filter by item ID"),
    field_id: Optional[str] = Query(None, description="Filter by field ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    db: Session = Depends(get_session),
) -> List[UsageLogOut]:
    """List usage logs."""
    usage_repo = UsageLogRepository(db)

    if item_id:
        logs = usage_repo.get_by_item(item_id, limit=limit)
    elif field_id:
        logs = usage_repo.get_by_field(field_id)
    else:
        logs = usage_repo.get_by_farmer(farmer_id, limit=limit)

    return [UsageLogOut.model_validate(log) for log in logs]


# Inventory Status and Validation
@router.get("/status", response_model=List[InventoryStatusResponse])
def get_inventory_status(
    farmer_id: str = Query(..., description="Farmer identifier"),
    category: Optional[InventoryCategory] = Query(None, description="Filter by category"),
    db: Session = Depends(get_session),
) -> List[InventoryStatusResponse]:
    """Get inventory status for all items (including depletion predictions)."""
    inventory_repo = InventoryRepository(db)
    usage_repo = UsageLogRepository(db)
    alert_repo = AlertRepository(db)
    predictor = DepletionPredictor(inventory_repo, usage_repo)

    items = inventory_repo.get_by_farmer(
        farmer_id=farmer_id,
        category=category.value if category else None,
        include_zero=False,
    )

    status_list = []
    for item in items:
        # Get depletion prediction
        prediction = predictor.predict_depletion(item.item_id)

        # Check alerts
        alerts = alert_repo.get_by_item(item.item_id, resolved=False)
        is_low_stock = any(a.alert_type == "low_stock" for a in alerts)
        is_critical = any(a.alert_type == "critical" for a in alerts)
        is_expiring = any(a.alert_type == "expiry" for a in alerts)

        status_list.append(
            InventoryStatusResponse(
                item_id=item.item_id,
                name=item.name,
                category=item.category,
                current_quantity=item.quantity,
                unit=item.unit,
                estimated_depletion_days=(
                    prediction.estimated_depletion_days if prediction else None
                ),
                is_low_stock=is_low_stock,
                is_critical=is_critical,
                is_expiring_soon=is_expiring,
                expiry_date=item.expiry_date,
            )
        )

    return status_list


@router.post("/validate", response_model=ActionValidationResponse)
def validate_action(
    request: ActionValidationRequest,
    db: Session = Depends(get_session),
    security: SecurityContext = Depends(require_service_token),
) -> ActionValidationResponse:
    """Validate that required inventory is available for an action.

    This endpoint MUST be called before any recommendation or scheduled action executes.
    """
    inventory_repo = InventoryRepository(db)
    validator = ActionValidator(inventory_repo)

    return validator.validate_action(request)


# Alerts
@router.get("/alerts", response_model=List[LowStockAlertResponse])
def get_alerts(
    farmer_id: str = Query(..., description="Farmer identifier"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    db: Session = Depends(get_session),
) -> List[LowStockAlertResponse]:
    """Get inventory alerts for a farmer."""
    alert_repo = AlertRepository(db)
    inventory_repo = InventoryRepository(db)

    alerts = alert_repo.get_by_farmer(farmer_id, resolved=resolved)

    alert_responses = []
    for alert in alerts:
        item = inventory_repo.get_by_id(alert.item_id)
        if item:
            alert_responses.append(
                LowStockAlertResponse(
                    alert_id=alert.alert_id,
                    item_id=alert.item_id,
                    item_name=item.name,
                    category=item.category,
                    current_quantity=item.quantity,
                    unit=item.unit,
                    alert_type=alert.alert_type,
                    severity=alert.severity,
                    message=alert.message,
                    created_at=alert.created_at,
                )
            )

    return alert_responses


@router.post("/alerts/{alert_id}/resolve", status_code=status.HTTP_200_OK)
def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_session),
) -> dict:
    """Mark an alert as resolved."""
    alert_repo = AlertRepository(db)
    alert = alert_repo.resolve(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    return {"status": "resolved", "alert_id": alert_id}


# Depletion Prediction
@router.get("/predict/{item_id}", response_model=DepletionPredictionResponse)
def predict_depletion(
    item_id: str,
    lookback_days: int = Query(7, ge=1, le=90, description="Days of history to use"),
    db: Session = Depends(get_session),
) -> DepletionPredictionResponse:
    """Predict when an inventory item will run out."""
    inventory_repo = InventoryRepository(db)
    usage_repo = UsageLogRepository(db)
    predictor = DepletionPredictor(inventory_repo, usage_repo)

    prediction = predictor.predict_depletion(item_id, lookback_days)
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item {item_id} not found or has zero quantity",
        )

    return prediction


# Economic Context
@router.get("/economic-context", response_model=EconomicContextResponse)
def get_economic_context(
    farmer_id: str = Query(..., description="Farmer identifier"),
    db: Session = Depends(get_session),
) -> EconomicContextResponse:
    """Get economic context about inventory investments and costs."""
    inventory_repo = InventoryRepository(db)
    usage_repo = UsageLogRepository(db)
    alert_repo = AlertRepository(db)
    economic_service = EconomicContextService(inventory_repo, usage_repo, alert_repo)

    return economic_service.get_economic_context(farmer_id)


# Summary
@router.get("/summary", response_model=InventorySummaryResponse)
def get_inventory_summary(
    farmer_id: str = Query(..., description="Farmer identifier"),
    db: Session = Depends(get_session),
) -> InventorySummaryResponse:
    """Get inventory summary for a farmer."""
    inventory_repo = InventoryRepository(db)
    usage_repo = UsageLogRepository(db)
    alert_repo = AlertRepository(db)

    items = inventory_repo.get_by_farmer(farmer_id, include_zero=False)

    total_value = Decimal("0.00")
    categories = {}
    low_stock_count = 0
    critical_count = 0
    expiring_soon_count = 0

    for item in items:
        total_value += item.quantity * item.cost_per_unit
        categories[item.category] = categories.get(item.category, 0) + 1

        # Check alerts
        alerts = alert_repo.get_by_item(item.item_id, resolved=False)
        if any(a.alert_type == "low_stock" for a in alerts):
            low_stock_count += 1
        if any(a.alert_type == "critical" for a in alerts):
            critical_count += 1
        if any(a.alert_type == "expiry" for a in alerts):
            expiring_soon_count += 1

    return InventorySummaryResponse(
        farmer_id=farmer_id,
        total_items=len(items),
        total_value=total_value,
        categories=categories,
        low_stock_count=low_stock_count,
        critical_count=critical_count,
        expiring_soon_count=expiring_soon_count,
    )
