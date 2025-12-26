"""Farm Inventory Engine - tracks stock and suggests shortages/alternatives.

This module currently uses a heuristic-based approach for MVP.
In production, integrate with:
- Inventory management system (stock ledger database)
- Vendor/supplier APIs for alternative products
- Purchase history and usage patterns for predictions
- Stock level alerts and reorder points
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class InventoryRepository:
    """Interface for inventory data storage and retrieval.

    TODO: Implement concrete backends:
        - SQLAlchemy ORM for PostgreSQL
        - Redis cache layer for fast lookups
        - ERP system integration (Odoo, SAP, etc.)
    """

    async def get_stock_level(self, item_id: str, farm_id: str) -> Optional[float]:
        """Get current stock quantity for an item."""
        raise NotImplementedError

    async def reserve_stock(self, item_id: str, farm_id: str, quantity: float) -> bool:
        """Reserve quantity from stock."""
        raise NotImplementedError

    async def get_alternatives(self, item_id: str) -> List[Dict[str, Any]]:
        """Get alternative products for a given item."""
        raise NotImplementedError


class StubInventoryRepository(InventoryRepository):
    """Stub implementation for MVP - returns hardcoded data."""

    async def get_stock_level(self, item_id: str, farm_id: str) -> Optional[float]:
        """Hardcoded stock levels for MVP."""
        stock = {
            "protective_gloves": 5.0,
            "pruning_shears": 2.0,
            "fungicide-X": 0.0,
            "fungicide-Y": 3.0,
            "insecticide-A": 2.5,
        }
        return stock.get(item_id, 0.0)

    async def get_alternatives(self, item_id: str) -> List[Dict[str, Any]]:
        """Hardcoded alternatives for MVP."""
        alternatives = {
            "fungicide-X": [
                {"id": "fungicide-Y", "name": "Fungicide Y", "ratio": 1.0},
                {"id": "fungicide-Z", "name": "Fungicide Z", "ratio": 0.8},
            ],
            "insecticide-A": [{"id": "insecticide-B", "name": "Insecticide B", "ratio": 1.2}],
        }
        return alternatives.get(item_id, [])


# Global inventory repo (swap implementation as needed)
_inventory_repo = StubInventoryRepository()


def plan_impact(plan: Dict[str, Any], farm_id: str = "default") -> dict:
    """Calculate inventory impact and shortages from action plan.

    Args:
        plan: Action plan with recommended interventions
        farm_id: Identifier for the farm (for multi-tenant scenarios)

    Returns:
        dict with:
            - reservations: List of items to reserve from stock
            - shortages: List of items with insufficient stock + alternatives

    TODO: Replace hardcoded logic:
        1. Parse plan.actions to extract required materials
        2. Query inventory repo for current stock levels
        3. Check against minimum thresholds
        4. Build shortages list with cost/priority ranking
        5. Fetch alternatives and suggest substitutions
    """
    import asyncio

    # For MVP: return stub data
    # In production: implement async inventory lookup and reservation

    reservations = [
        {"item": "protective_gloves", "qty": 1, "reason": "disease_scouting"},
        {"item": "pruning_shears", "qty": 1, "reason": "canopy_management"},
    ]

    shortages = [
        {
            "item": "fungicide-X",
            "qty_needed": 1,
            "qty_available": 0,
            "suggested_substitute": "fungicide-Y",
            "substitute_qty": 1,
            "estimated_cost_usd": 45.0,
        }
    ]

    return {
        "reservations": reservations,
        "shortages": shortages,
        "total_cost_usd": sum(s.get("estimated_cost_usd", 0) for s in shortages),
        "note": "MVP hardcoded inventory. Integrate with real stock ledger for accuracy.",
    }
