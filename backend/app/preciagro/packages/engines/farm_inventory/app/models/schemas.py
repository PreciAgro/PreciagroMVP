"""Pydantic schemas for Farm Inventory Engine API."""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class InventoryCategory(str, Enum):
    """Inventory item categories."""

    SEED = "seed"
    FERTILIZER = "fertilizer"
    CHEMICAL = "chemical"
    FEED = "feed"
    TOOL = "tool"


class InventoryUnit(str, Enum):
    """Inventory quantity units."""

    KG = "kg"
    LITERS = "liters"
    UNITS = "units"
    TONS = "tons"
    BAGS = "bags"


class UsageReason(str, Enum):
    """Reason for inventory usage."""

    RECOMMENDATION = "recommendation"
    MANUAL = "manual"
    EMERGENCY = "emergency"
    SCHEDULED = "scheduled"


# Request Schemas
class InventoryItemCreate(BaseModel):
    """Schema for creating an inventory item."""

    farmer_id: str = Field(..., description="Farmer identifier")
    category: InventoryCategory = Field(..., description="Item category")
    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    crop_or_animal: Optional[str] = Field(None, max_length=100, description="Target crop or animal")
    quantity: Decimal = Field(..., ge=0, description="Initial quantity")
    unit: InventoryUnit = Field(..., description="Quantity unit")
    batch_id: Optional[str] = Field(None, max_length=100, description="Batch identifier")
    expiry_date: Optional[date] = Field(None, description="Expiry date")
    purchase_date: Optional[date] = Field(None, description="Purchase date")
    cost_per_unit: Decimal = Field(..., ge=0, description="Cost per unit")
    storage_condition: Optional[str] = Field(
        None, max_length=200, description="Storage requirements"
    )
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class InventoryItemUpdate(BaseModel):
    """Schema for updating an inventory item."""

    quantity: Optional[Decimal] = Field(None, ge=0, description="New quantity")
    cost_per_unit: Optional[Decimal] = Field(None, ge=0, description="Updated cost per unit")
    expiry_date: Optional[date] = Field(None, description="Updated expiry date")
    storage_condition: Optional[str] = Field(
        None, max_length=200, description="Storage requirements"
    )
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class UsageLogCreate(BaseModel):
    """Schema for recording inventory usage."""

    item_id: str = Field(..., description="Inventory item identifier")
    farmer_id: str = Field(..., description="Farmer identifier")
    field_id: Optional[str] = Field(None, description="Field identifier")
    crop_stage: Optional[str] = Field(None, max_length=50, description="Crop growth stage")
    quantity_used: Decimal = Field(..., gt=0, description="Quantity used (must be positive)")
    usage_reason: UsageReason = Field(..., description="Reason for usage")
    source_engine: Optional[str] = Field(
        None,
        max_length=50,
        description="Engine that triggered this usage: crop_intelligence, temporal_logic, manual, emergency",
    )
    action_id: Optional[str] = Field(
        None,
        max_length=100,
        description="ID of the action/recommendation/task that caused this usage",
    )
    metadata: Optional[dict] = Field(None, description="Additional metadata")

    @field_validator("quantity_used")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("quantity_used must be positive")
        return v


class ActionValidationRequest(BaseModel):
    """Schema for validating an action against inventory."""

    farmer_id: str = Field(..., description="Farmer identifier")
    field_id: Optional[str] = Field(None, description="Field identifier")
    required_items: list[dict] = Field(..., description="List of required items with quantities")
    # Format: [{"item_id": "uuid", "quantity": 10.5, "unit": "kg"}, ...]


# Response Schemas
class InventoryItemOut(BaseModel):
    """Schema for inventory item response."""

    item_id: str
    farmer_id: str
    category: InventoryCategory
    name: str
    crop_or_animal: Optional[str]
    quantity: Decimal
    unit: InventoryUnit
    batch_id: Optional[str]
    expiry_date: Optional[date]
    purchase_date: Optional[date]
    cost_per_unit: Decimal
    storage_condition: Optional[str]
    last_updated: datetime
    created_at: datetime
    metadata: Optional[dict]

    class Config:
        from_attributes = True


class UsageLogOut(BaseModel):
    """Schema for usage log response."""

    usage_id: str
    item_id: str
    farmer_id: str
    field_id: Optional[str]
    crop_stage: Optional[str]
    quantity_used: Decimal
    usage_reason: UsageReason
    source_engine: Optional[str]
    action_id: Optional[str]
    timestamp: datetime
    metadata: Optional[dict]

    class Config:
        from_attributes = True


class InventoryStatusResponse(BaseModel):
    """Schema for inventory status response."""

    item_id: str
    name: str
    category: InventoryCategory
    current_quantity: Decimal
    unit: InventoryUnit
    estimated_depletion_days: Optional[int] = Field(
        None, description="Days until depletion (if predictable)"
    )
    is_low_stock: bool
    is_critical: bool
    is_expiring_soon: bool
    expiry_date: Optional[date]


class LowStockAlertResponse(BaseModel):
    """Schema for low stock alert response."""

    alert_id: str
    item_id: str
    item_name: str
    category: InventoryCategory
    current_quantity: Decimal
    unit: InventoryUnit
    alert_type: str
    severity: str
    message: str
    created_at: datetime


class ActionValidationResponse(BaseModel):
    """Schema for action validation response."""

    is_valid: bool
    missing_items: list[dict] = Field(
        default_factory=list, description="Items with insufficient stock"
    )
    available_items: list[dict] = Field(
        default_factory=list, description="Items with sufficient stock"
    )
    total_cost: Decimal = Field(default=Decimal("0.00"), description="Total cost of required items")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class DepletionPredictionResponse(BaseModel):
    """Schema for depletion prediction response."""

    item_id: str
    item_name: str
    current_quantity: Decimal
    unit: InventoryUnit
    estimated_daily_usage: Decimal
    estimated_depletion_days: Optional[int]
    confidence: float = Field(..., ge=0, le=1, description="Confidence in prediction (0-1)")
    prediction_basis: str = Field(..., description="Explanation of prediction")


class EconomicContextResponse(BaseModel):
    """Schema for economic context response."""

    farmer_id: str
    total_invested_cost: Decimal = Field(
        ..., description="Total cost already invested in inventory"
    )
    estimated_remaining_cost: Decimal = Field(..., description="Estimated cost until harvest")
    items_count: int
    low_stock_items_count: int
    critical_items_count: int
    expiring_soon_count: int


class InventorySummaryResponse(BaseModel):
    """Schema for inventory summary response."""

    farmer_id: str
    total_items: int
    total_value: Decimal
    categories: dict[str, int] = Field(default_factory=dict, description="Item count by category")
    low_stock_count: int
    critical_count: int
    expiring_soon_count: int
