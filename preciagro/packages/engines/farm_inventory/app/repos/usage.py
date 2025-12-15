"""Repository for usage log data access."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from ..db import models
from ..models.schemas import UsageLogCreate, UsageLogOut


class UsageLogRepository:
    """Handles persistence of usage logs (never deleted)."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, usage_data: UsageLogCreate) -> models.UsageLog:
        """Create a new usage log entry."""
        db_log = models.UsageLog(
            item_id=usage_data.item_id,
            farmer_id=usage_data.farmer_id,
            field_id=usage_data.field_id,
            crop_stage=usage_data.crop_stage,
            quantity_used=usage_data.quantity_used,
            usage_reason=usage_data.usage_reason.value,
            source_engine=usage_data.source_engine,
            action_id=usage_data.action_id,
            metadata_=usage_data.metadata,
        )
        self.session.add(db_log)
        self.session.flush()
        return db_log

    def get_by_id(self, usage_id: str) -> Optional[models.UsageLog]:
        """Get usage log by ID."""
        return self.session.get(models.UsageLog, usage_id)

    def get_by_item(
        self,
        item_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[models.UsageLog]:
        """Get usage logs for an item, optionally filtered by date range."""
        query = self.session.query(models.UsageLog).filter(models.UsageLog.item_id == item_id)

        if start_date:
            query = query.filter(models.UsageLog.timestamp >= start_date)
        if end_date:
            query = query.filter(models.UsageLog.timestamp <= end_date)

        query = query.order_by(desc(models.UsageLog.timestamp))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_farmer(
        self,
        farmer_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[models.UsageLog]:
        """Get usage logs for a farmer, optionally filtered by date range."""
        query = self.session.query(models.UsageLog).filter(models.UsageLog.farmer_id == farmer_id)

        if start_date:
            query = query.filter(models.UsageLog.timestamp >= start_date)
        if end_date:
            query = query.filter(models.UsageLog.timestamp <= end_date)

        query = query.order_by(desc(models.UsageLog.timestamp))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_field(
        self,
        field_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[models.UsageLog]:
        """Get usage logs for a field."""
        query = self.session.query(models.UsageLog).filter(models.UsageLog.field_id == field_id)

        if start_date:
            query = query.filter(models.UsageLog.timestamp >= start_date)
        if end_date:
            query = query.filter(models.UsageLog.timestamp <= end_date)

        return query.order_by(desc(models.UsageLog.timestamp)).all()

    def calculate_usage_rate(self, item_id: str, days: int = 7) -> Optional[Decimal]:
        """Calculate average daily usage rate for an item over the last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)

        result = (
            self.session.query(func.sum(models.UsageLog.quantity_used))
            .filter(
                and_(
                    models.UsageLog.item_id == item_id,
                    models.UsageLog.timestamp >= start_date,
                )
            )
            .scalar()
        )

        if result is None:
            return None

        total_usage = Decimal(str(result))
        if total_usage == 0:
            return Decimal("0.00")

        return total_usage / Decimal(str(days))

    def get_total_usage(self, item_id: str, start_date: Optional[datetime] = None) -> Decimal:
        """Get total usage for an item, optionally from a start date."""
        query = self.session.query(func.sum(models.UsageLog.quantity_used)).filter(
            models.UsageLog.item_id == item_id
        )

        if start_date:
            query = query.filter(models.UsageLog.timestamp >= start_date)

        result = query.scalar()
        return Decimal(str(result)) if result else Decimal("0.00")
