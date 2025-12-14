"""Repository for inventory item data access."""

from __future__ import annotations

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..db import models
from ..models.schemas import InventoryItemCreate, InventoryItemUpdate, InventoryItemOut


class InventoryRepository:
    """Handles persistence of inventory items."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, item_data: InventoryItemCreate) -> models.InventoryItem:
        """Create a new inventory item."""
        db_item = models.InventoryItem(
            farmer_id=item_data.farmer_id,
            category=item_data.category.value,
            name=item_data.name,
            crop_or_animal=item_data.crop_or_animal,
            quantity=item_data.quantity,
            unit=item_data.unit.value,
            batch_id=item_data.batch_id,
            expiry_date=item_data.expiry_date,
            purchase_date=item_data.purchase_date,
            cost_per_unit=item_data.cost_per_unit,
            storage_condition=item_data.storage_condition,
            metadata_=item_data.metadata,
        )
        self.session.add(db_item)
        self.session.flush()
        return db_item

    def get_by_id(self, item_id: str) -> Optional[models.InventoryItem]:
        """Get inventory item by ID."""
        return self.session.get(models.InventoryItem, item_id)

    def get_by_farmer(
        self,
        farmer_id: str,
        category: Optional[str] = None,
        include_zero: bool = False,
    ) -> List[models.InventoryItem]:
        """Get all inventory items for a farmer, optionally filtered by category."""
        query = self.session.query(models.InventoryItem).filter(
            models.InventoryItem.farmer_id == farmer_id
        )
        
        if category:
            query = query.filter(models.InventoryItem.category == category)
        
        if not include_zero:
            query = query.filter(models.InventoryItem.quantity > 0)
        
        return query.order_by(models.InventoryItem.last_updated.desc()).all()

    def update(
        self, item_id: str, update_data: InventoryItemUpdate
    ) -> Optional[models.InventoryItem]:
        """Update an inventory item."""
        db_item = self.get_by_id(item_id)
        if not db_item:
            return None
        
        if update_data.quantity is not None:
            db_item.quantity = update_data.quantity
        if update_data.cost_per_unit is not None:
            db_item.cost_per_unit = update_data.cost_per_unit
        if update_data.expiry_date is not None:
            db_item.expiry_date = update_data.expiry_date
        if update_data.storage_condition is not None:
            db_item.storage_condition = update_data.storage_condition
        if update_data.metadata is not None:
            db_item.metadata_ = update_data.metadata
        
        db_item.last_updated = datetime.utcnow()
        self.session.flush()
        return db_item

    def deduct_quantity(
        self, item_id: str, quantity: Decimal, allow_negative: bool = False
    ) -> Optional[models.InventoryItem]:
        """Deduct quantity from inventory item with transaction locking.
        
        Uses SELECT FOR UPDATE to prevent race conditions when multiple
        engines attempt to deduct simultaneously.
        
        Returns None if insufficient stock.
        """
        # Use SELECT FOR UPDATE to lock the row for this transaction
        db_item = (
            self.session.query(models.InventoryItem)
            .filter(models.InventoryItem.item_id == item_id)
            .with_for_update()
            .first()
        )
        
        if not db_item:
            return None
        
        new_quantity = db_item.quantity - quantity
        if new_quantity < 0 and not allow_negative:
            return None
        
        db_item.quantity = new_quantity
        db_item.last_updated = datetime.utcnow()
        self.session.flush()
        return db_item

    def add_quantity(self, item_id: str, quantity: Decimal) -> Optional[models.InventoryItem]:
        """Add quantity to inventory item with transaction locking."""
        # Use SELECT FOR UPDATE to lock the row for this transaction
        db_item = (
            self.session.query(models.InventoryItem)
            .filter(models.InventoryItem.item_id == item_id)
            .with_for_update()
            .first()
        )
        
        if not db_item:
            return None
        
        db_item.quantity += quantity
        db_item.last_updated = datetime.utcnow()
        self.session.flush()
        return db_item

    def get_expiring_soon(
        self, farmer_id: str, days_ahead: int = 30
    ) -> List[models.InventoryItem]:
        """Get items expiring within specified days."""
        cutoff_date = date.today() + datetime.timedelta(days=days_ahead)
        return (
            self.session.query(models.InventoryItem)
            .filter(
                and_(
                    models.InventoryItem.farmer_id == farmer_id,
                    models.InventoryItem.expiry_date.isnot(None),
                    models.InventoryItem.expiry_date <= cutoff_date,
                    models.InventoryItem.quantity > 0,
                )
            )
            .order_by(models.InventoryItem.expiry_date.asc())
            .all()
        )

    def get_low_stock_items(
        self, farmer_id: str, threshold_ratio: float = 0.2
    ) -> List[models.InventoryItem]:
        """Get items with low stock (below threshold ratio of typical usage).
        
        Note: This is a simple implementation. In production, this should
        consider historical usage patterns per item.
        """
        # For MVP, we'll use a simple heuristic: items with quantity < threshold
        # In production, this should compare against historical usage rates
        return (
            self.session.query(models.InventoryItem)
            .filter(
                and_(
                    models.InventoryItem.farmer_id == farmer_id,
                    models.InventoryItem.quantity > 0,
                )
            )
            .all()
        )

    def delete(self, item_id: str) -> bool:
        """Delete an inventory item (soft delete by setting quantity to 0)."""
        db_item = self.get_by_id(item_id)
        if not db_item:
            return False
        
        # Soft delete: set quantity to 0 rather than actually deleting
        db_item.quantity = Decimal("0.00")
        db_item.last_updated = datetime.utcnow()
        self.session.flush()
        return True

