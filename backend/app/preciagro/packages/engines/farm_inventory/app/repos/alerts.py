"""Repository for alert data access."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..db import models


class AlertRepository:
    """Handles persistence of inventory alerts."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        farmer_id: str,
        item_id: str,
        alert_type: str,
        severity: str,
        message: str,
        metadata: Optional[dict] = None,
    ) -> models.InventoryAlert:
        """Create a new alert."""
        db_alert = models.InventoryAlert(
            farmer_id=farmer_id,
            item_id=item_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata_=metadata,
        )
        self.session.add(db_alert)
        self.session.flush()
        return db_alert

    def get_by_farmer(
        self, farmer_id: str, resolved: Optional[bool] = None
    ) -> List[models.InventoryAlert]:
        """Get alerts for a farmer, optionally filtered by resolved status."""
        query = self.session.query(models.InventoryAlert).filter(
            models.InventoryAlert.farmer_id == farmer_id
        )

        if resolved is not None:
            query = query.filter(models.InventoryAlert.resolved == resolved)

        return query.order_by(models.InventoryAlert.created_at.desc()).all()

    def get_by_item(
        self, item_id: str, resolved: Optional[bool] = None
    ) -> List[models.InventoryAlert]:
        """Get alerts for an item."""
        query = self.session.query(models.InventoryAlert).filter(
            models.InventoryAlert.item_id == item_id
        )

        if resolved is not None:
            query = query.filter(models.InventoryAlert.resolved == resolved)

        return query.order_by(models.InventoryAlert.created_at.desc()).all()

    def resolve(self, alert_id: str) -> Optional[models.InventoryAlert]:
        """Mark an alert as resolved."""
        db_alert = self.session.get(models.InventoryAlert, alert_id)
        if not db_alert:
            return None

        db_alert.resolved = True
        db_alert.resolved_at = datetime.utcnow()
        self.session.flush()
        return db_alert

    def get_critical_alerts(self, farmer_id: str) -> List[models.InventoryAlert]:
        """Get unresolved critical alerts for a farmer."""
        return (
            self.session.query(models.InventoryAlert)
            .filter(
                and_(
                    models.InventoryAlert.farmer_id == farmer_id,
                    models.InventoryAlert.severity == "critical",
                    models.InventoryAlert.resolved == False,
                )
            )
            .order_by(models.InventoryAlert.created_at.desc())
            .all()
        )
