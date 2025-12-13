"""Repository for inventory snapshot data access."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from ..db import models


class SnapshotRepository:
    """Handles persistence of inventory snapshots."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        farmer_id: str,
        snapshot_type: str,
        snapshot_data: dict,
        triggered_by: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> models.InventorySnapshot:
        """Create a new inventory snapshot."""
        db_snapshot = models.InventorySnapshot(
            farmer_id=farmer_id,
            snapshot_type=snapshot_type,
            triggered_by=triggered_by,
            snapshot_data=snapshot_data,
            metadata_=metadata,
        )
        self.session.add(db_snapshot)
        self.session.flush()
        return db_snapshot

    def get_by_id(self, snapshot_id: str) -> Optional[models.InventorySnapshot]:
        """Get snapshot by ID."""
        return self.session.get(models.InventorySnapshot, snapshot_id)

    def get_by_farmer(
        self,
        farmer_id: str,
        snapshot_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[models.InventorySnapshot]:
        """Get snapshots for a farmer."""
        query = self.session.query(models.InventorySnapshot).filter(
            models.InventorySnapshot.farmer_id == farmer_id
        )
        
        if snapshot_type:
            query = query.filter(models.InventorySnapshot.snapshot_type == snapshot_type)
        
        query = query.order_by(models.InventorySnapshot.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    def get_latest(
        self, farmer_id: str, snapshot_type: Optional[str] = None
    ) -> Optional[models.InventorySnapshot]:
        """Get the latest snapshot for a farmer."""
        query = self.session.query(models.InventorySnapshot).filter(
            models.InventorySnapshot.farmer_id == farmer_id
        )
        
        if snapshot_type:
            query = query.filter(models.InventorySnapshot.snapshot_type == snapshot_type)
        
        return query.order_by(models.InventorySnapshot.created_at.desc()).first()

