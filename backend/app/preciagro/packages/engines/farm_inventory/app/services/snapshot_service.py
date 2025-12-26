"""Service for creating inventory snapshots."""

from __future__ import annotations

from typing import Optional
import logging

from ..repos.inventory import InventoryRepository
from ..repos.snapshots import SnapshotRepository

logger = logging.getLogger(__name__)


class SnapshotService:
    """Service for creating inventory snapshots for auditability."""

    def __init__(
        self,
        inventory_repo: InventoryRepository,
        snapshot_repo: SnapshotRepository,
    ):
        self.inventory_repo = inventory_repo
        self.snapshot_repo = snapshot_repo

    def create_snapshot(
        self,
        farmer_id: str,
        snapshot_type: str,
        triggered_by: Optional[str] = None,
    ) -> dict:
        """Create a snapshot of current inventory state.

        Args:
            farmer_id: Farmer identifier
            snapshot_type: Type of snapshot ("daily", "pre_action", "manual")
            triggered_by: What triggered this snapshot (action_id, user_id, "system")

        Returns:
            Snapshot data
        """
        items = self.inventory_repo.get_by_farmer(farmer_id, include_zero=False)

        snapshot_data = []
        for item in items:
            snapshot_data.append(
                {
                    "item_id": item.item_id,
                    "name": item.name,
                    "category": item.category,
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "cost_per_unit": float(item.cost_per_unit),
                    "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
                }
            )

        snapshot = self.snapshot_repo.create(
            farmer_id=farmer_id,
            snapshot_type=snapshot_type,
            snapshot_data={"items": snapshot_data, "total_items": len(items)},
            triggered_by=triggered_by,
        )

        logger.info(
            f"Created inventory snapshot {snapshot.snapshot_id} for farmer {farmer_id}, "
            f"type={snapshot_type}, items={len(items)}"
        )

        return {
            "snapshot_id": snapshot.snapshot_id,
            "farmer_id": farmer_id,
            "snapshot_type": snapshot_type,
            "item_count": len(items),
            "created_at": snapshot.created_at.isoformat(),
        }

    def create_pre_action_snapshot(self, farmer_id: str, action_id: str) -> dict:
        """Create a snapshot before executing an action.

        This allows us to answer: "What was the inventory when this
        recommendation was made?"
        """
        return self.create_snapshot(
            farmer_id=farmer_id,
            snapshot_type="pre_action",
            triggered_by=action_id,
        )
