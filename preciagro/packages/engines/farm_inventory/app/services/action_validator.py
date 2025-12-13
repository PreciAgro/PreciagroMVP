"""Service for validating actions against inventory availability."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Dict, Any
import logging

from ..repos.inventory import InventoryRepository
from ..models.schemas import ActionValidationRequest, ActionValidationResponse

logger = logging.getLogger(__name__)


class ActionValidator:
    """Validates that required inventory is available for actions."""

    def __init__(self, inventory_repo: InventoryRepository):
        self.inventory_repo = inventory_repo

    def validate_action(
        self, request: ActionValidationRequest
    ) -> ActionValidationResponse:
        """Validate that all required items are available in inventory.
        
        This is the core validation method that must be called before
        any recommendation or scheduled action executes.
        """
        missing_items: List[Dict[str, Any]] = []
        available_items: List[Dict[str, Any]] = []
        warnings: List[str] = []
        total_cost = Decimal("0.00")

        for required_item in request.required_items:
            item_id = required_item.get("item_id")
            required_quantity = Decimal(str(required_item.get("quantity", 0)))
            required_unit = required_item.get("unit", "")

            if not item_id or required_quantity <= 0:
                warnings.append(f"Invalid item requirement: {required_item}")
                continue

            # Get inventory item
            item = self.inventory_repo.get_by_id(item_id)
            
            if not item:
                missing_items.append({
                    "item_id": item_id,
                    "item_name": required_item.get("name", "Unknown"),
                    "required_quantity": float(required_quantity),
                    "required_unit": required_unit,
                    "available_quantity": 0.0,
                    "available_unit": required_unit,
                    "shortage": float(required_quantity),
                })
                total_cost += required_quantity * Decimal("0.00")  # Unknown cost
                continue

            # Check unit compatibility (simplified for MVP)
            if item.unit != required_unit:
                warnings.append(
                    f"Unit mismatch for {item.name}: inventory has {item.unit}, "
                    f"required {required_unit}"
                )

            # Check expiry - CRITICAL: expired items must fail or require confirmation
            is_expired = False
            if item.expiry_date and item.expiry_date < date.today():
                is_expired = True
                missing_items.append({
                    "item_id": item_id,
                    "item_name": item.name,
                    "required_quantity": float(required_quantity),
                    "required_unit": item.unit,
                    "available_quantity": float(item.quantity),
                    "available_unit": item.unit,
                    "shortage": float(required_quantity),
                    "expired": True,
                    "expiry_date": item.expiry_date.isoformat(),
                    "reason": f"Item expired on {item.expiry_date.isoformat()}",
                })
                total_cost += item.cost_per_unit * required_quantity
                logger.warning(
                    f"Validation failed: expired item {item_id} ({item.name}) "
                    f"expired on {item.expiry_date}"
                )
                continue
            
            # Check expiry warning (expiring soon)
            is_expiring_soon = False
            if item.expiry_date:
                days_until_expiry = (item.expiry_date - date.today()).days
                if 0 <= days_until_expiry <= 30:
                    is_expiring_soon = True
                    warnings.append(
                        f"{item.name} expires in {days_until_expiry} days "
                        f"(on {item.expiry_date.isoformat()})"
                    )

            # Check availability
            if item.quantity >= required_quantity:
                item_data = {
                    "item_id": item_id,
                    "item_name": item.name,
                    "required_quantity": float(required_quantity),
                    "available_quantity": float(item.quantity),
                    "unit": item.unit,
                    "cost": float(item.cost_per_unit * required_quantity),
                }
                if is_expiring_soon:
                    item_data["expiring_soon"] = True
                    item_data["expiry_date"] = item.expiry_date.isoformat()
                
                available_items.append(item_data)
                total_cost += item.cost_per_unit * required_quantity
            else:
                shortage = required_quantity - item.quantity
                missing_items.append({
                    "item_id": item_id,
                    "item_name": item.name,
                    "required_quantity": float(required_quantity),
                    "required_unit": item.unit,
                    "available_quantity": float(item.quantity),
                    "available_unit": item.unit,
                    "shortage": float(shortage),
                    "cost_if_purchased": float(item.cost_per_unit * shortage),
                })
                total_cost += item.cost_per_unit * required_quantity

        # Check for low stock warnings
        for available_item in available_items:
            item = self.inventory_repo.get_by_id(available_item["item_id"])
            if item:
                # Simple heuristic: warn if usage would leave < 20% remaining
                remaining_after_use = item.quantity - Decimal(str(available_item["required_quantity"]))
                if remaining_after_use > 0 and remaining_after_use < item.quantity * Decimal("0.2"):
                    warnings.append(
                        f"Using {item.name} will leave low stock: "
                        f"{remaining_after_use:.2f} {item.unit} remaining"
                    )

        is_valid = len(missing_items) == 0

        # Log validation result for observability
        logger.info(
            f"Action validation for farmer {request.farmer_id}: "
            f"valid={is_valid}, missing={len(missing_items)}, "
            f"available={len(available_items)}, warnings={len(warnings)}"
        )

        return ActionValidationResponse(
            is_valid=is_valid,
            missing_items=missing_items,
            available_items=available_items,
            total_cost=total_cost,
            warnings=warnings,
        )

    def check_item_availability(
        self, item_id: str, required_quantity: Decimal
    ) -> bool:
        """Quick check if an item has sufficient quantity."""
        item = self.inventory_repo.get_by_id(item_id)
        if not item:
            return False
        return item.quantity >= required_quantity

