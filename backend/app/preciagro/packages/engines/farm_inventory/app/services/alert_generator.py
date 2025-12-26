"""Service for generating inventory alerts."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List

from ..repos.inventory import InventoryRepository
from ..repos.alerts import AlertRepository
from ..repos.usage import UsageLogRepository
from ..core.config import settings
from ..db import models


class AlertGenerator:
    """Generates alerts for low stock, critical shortages, and expiry."""

    def __init__(
        self,
        inventory_repo: InventoryRepository,
        alert_repo: AlertRepository,
        usage_repo: UsageLogRepository,
    ):
        self.inventory_repo = inventory_repo
        self.alert_repo = alert_repo
        self.usage_repo = usage_repo

    def generate_alerts_for_farmer(self, farmer_id: str) -> List[models.InventoryAlert]:
        """Generate all alerts for a farmer's inventory."""
        alerts = []

        items = self.inventory_repo.get_by_farmer(farmer_id, include_zero=False)

        for item in items:
            # Check for low stock
            low_stock_alert = self._check_low_stock(item, farmer_id)
            if low_stock_alert:
                alerts.append(low_stock_alert)

            # Check for critical stock
            critical_alert = self._check_critical_stock(item, farmer_id)
            if critical_alert:
                alerts.append(critical_alert)

            # Check for expiry
            expiry_alert = self._check_expiry(item, farmer_id)
            if expiry_alert:
                alerts.append(expiry_alert)

        return alerts

    def _check_low_stock(
        self, item: models.InventoryItem, farmer_id: str
    ) -> models.InventoryAlert | None:
        """Check if item is low stock and create alert if needed.

        Implements deduplication: only creates alert if no unresolved
        alert of the same type exists for this item.
        """
        # Calculate typical usage rate
        daily_usage = self.usage_repo.calculate_usage_rate(
            item.item_id, days=settings.DEFAULT_USAGE_RATE_DAYS
        )

        # Check for existing unresolved alert (deduplication)
        existing = self.alert_repo.get_by_item(item.item_id, resolved=False)
        for alert in existing:
            if alert.alert_type == "low_stock":
                return None  # Alert already exists, skip

        if daily_usage is None or daily_usage == 0:
            # No usage history - use simple threshold
            # For MVP, consider items with quantity < 10 units as low stock
            threshold = Decimal("10.00")
            if item.quantity < threshold:
                return self.alert_repo.create(
                    farmer_id=farmer_id,
                    item_id=item.item_id,
                    alert_type="low_stock",
                    severity="warning",
                    message=f"{item.name} is running low. Current stock: {item.quantity} {item.unit}",
                )
        else:
            # Calculate days of stock remaining
            days_remaining = item.quantity / daily_usage if daily_usage > 0 else None

            if days_remaining and days_remaining <= settings.LOW_STOCK_THRESHOLD * 30:
                return self.alert_repo.create(
                    farmer_id=farmer_id,
                    item_id=item.item_id,
                    alert_type="low_stock",
                    severity="warning",
                    message=(
                        f"{item.name} is running low. "
                        f"Current stock: {item.quantity} {item.unit}. "
                        f"Estimated days remaining: {int(days_remaining)}"
                    ),
                )

        return None

    def _check_critical_stock(
        self, item: models.InventoryItem, farmer_id: str
    ) -> models.InventoryAlert | None:
        """Check if item is critically low and create alert if needed.

        Implements deduplication: only creates alert if no unresolved
        alert of the same type exists for this item.
        """
        daily_usage = self.usage_repo.calculate_usage_rate(
            item.item_id, days=settings.DEFAULT_USAGE_RATE_DAYS
        )

        # Check for existing unresolved alert (deduplication)
        existing = self.alert_repo.get_by_item(item.item_id, resolved=False)
        for alert in existing:
            if alert.alert_type == "critical":
                return None  # Alert already exists, skip

        if daily_usage is None or daily_usage == 0:
            # No usage history - use simple threshold
            threshold = Decimal("2.00")
            if item.quantity < threshold:
                return self.alert_repo.create(
                    farmer_id=farmer_id,
                    item_id=item.item_id,
                    alert_type="critical",
                    severity="critical",
                    message=(
                        f"CRITICAL: {item.name} is almost out! "
                        f"Current stock: {item.quantity} {item.unit}. "
                        f"Replenish immediately."
                    ),
                )
        else:
            # Calculate days of stock remaining
            days_remaining = item.quantity / daily_usage if daily_usage > 0 else None

            if days_remaining and days_remaining <= settings.CRITICAL_STOCK_THRESHOLD * 30:
                return self.alert_repo.create(
                    farmer_id=farmer_id,
                    item_id=item.item_id,
                    alert_type="critical",
                    severity="critical",
                    message=(
                        f"CRITICAL: {item.name} will run out in {int(days_remaining)} days! "
                        f"Current stock: {item.quantity} {item.unit}. "
                        f"Replenish immediately."
                    ),
                )

        return None

    def _check_expiry(
        self, item: models.InventoryItem, farmer_id: str
    ) -> models.InventoryAlert | None:
        """Check if item is expiring soon and create alert if needed.

        Implements deduplication: only creates alert if no unresolved
        alert of the same type exists for this item.
        """
        if not item.expiry_date or item.quantity <= 0:
            return None

        # Check for existing unresolved alert (deduplication)
        existing = self.alert_repo.get_by_item(item.item_id, resolved=False)
        for alert in existing:
            if alert.alert_type == "expiry":
                return None  # Alert already exists, skip

        days_until_expiry = (item.expiry_date - date.today()).days

        if 0 <= days_until_expiry <= settings.EXPIRY_WARNING_DAYS:
            severity = "critical" if days_until_expiry <= 7 else "warning"
            message = (
                f"{item.name} expires in {days_until_expiry} days "
                f"(on {item.expiry_date}). "
                f"Current stock: {item.quantity} {item.unit}. "
                f"Use or dispose before expiry."
            )

            return self.alert_repo.create(
                farmer_id=farmer_id,
                item_id=item.item_id,
                alert_type="expiry",
                severity=severity,
                message=message,
            )

        return None
