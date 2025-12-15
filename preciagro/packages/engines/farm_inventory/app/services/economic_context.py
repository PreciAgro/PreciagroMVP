"""Service for providing economic context about inventory."""

from __future__ import annotations

from decimal import Decimal
from datetime import date, timedelta

from ..repos.inventory import InventoryRepository
from ..repos.usage import UsageLogRepository
from ..repos.alerts import AlertRepository
from ..models.schemas import EconomicContextResponse
from ..core.config import settings


class EconomicContextService:
    """Provides economic context about inventory investments and costs."""

    def __init__(
        self,
        inventory_repo: InventoryRepository,
        usage_repo: UsageLogRepository,
        alert_repo: AlertRepository,
    ):
        self.inventory_repo = inventory_repo
        self.usage_repo = usage_repo
        self.alert_repo = alert_repo

    def get_economic_context(self, farmer_id: str) -> EconomicContextResponse:
        """Calculate economic context for a farmer's inventory."""
        items = self.inventory_repo.get_by_farmer(farmer_id, include_zero=False)

        # Calculate total invested cost
        total_invested = Decimal("0.00")
        for item in items:
            total_invested += item.quantity * item.cost_per_unit

        # Estimate remaining cost until harvest
        # This is a simplified calculation - in production, this would:
        # 1. Get crop plans from Crop Intelligence Engine
        # 2. Calculate required inputs per growth stage
        # 3. Estimate costs based on usage rates
        estimated_remaining = self._estimate_remaining_cost(items)

        # Count items by status
        low_stock_count = 0
        critical_count = 0
        expiring_soon_count = 0

        for item in items:
            # Check low stock
            daily_usage = self.usage_repo.calculate_usage_rate(
                item.item_id, days=settings.DEFAULT_USAGE_RATE_DAYS
            )
            if daily_usage and daily_usage > 0:
                days_remaining = item.quantity / daily_usage
                if days_remaining <= settings.LOW_STOCK_THRESHOLD * 30:
                    low_stock_count += 1
                if days_remaining <= settings.CRITICAL_STOCK_THRESHOLD * 30:
                    critical_count += 1
            else:
                # Simple threshold for items without usage history
                if item.quantity < Decimal("10.00"):
                    low_stock_count += 1
                if item.quantity < Decimal("2.00"):
                    critical_count += 1

            # Check expiry
            if item.expiry_date:
                days_until_expiry = (item.expiry_date - date.today()).days
                if 0 <= days_until_expiry <= settings.EXPIRY_WARNING_DAYS:
                    expiring_soon_count += 1

        return EconomicContextResponse(
            farmer_id=farmer_id,
            total_invested_cost=total_invested,
            estimated_remaining_cost=estimated_remaining,
            items_count=len(items),
            low_stock_items_count=low_stock_count,
            critical_items_count=critical_count,
            expiring_soon_count=expiring_soon_count,
        )

    def _estimate_remaining_cost(self, items: list) -> Decimal:
        """Estimate remaining cost until harvest.

        For MVP, this is a simplified calculation. In production, this would:
        1. Integrate with Crop Intelligence Engine for crop plans
        2. Get growth stage predictions
        3. Calculate required inputs per stage
        4. Estimate costs based on current prices
        """
        # Simplified: estimate based on historical usage rates
        # Assume average usage continues for next 90 days
        estimated = Decimal("0.00")

        for item in items:
            daily_usage = self.usage_repo.calculate_usage_rate(
                item.item_id, days=settings.DEFAULT_USAGE_RATE_DAYS
            )

            if daily_usage and daily_usage > 0:
                # Estimate usage for next 90 days
                estimated_usage = daily_usage * Decimal("90")
                # Only count if we'll need to purchase more
                if estimated_usage > item.quantity:
                    additional_needed = estimated_usage - item.quantity
                    estimated += additional_needed * item.cost_per_unit

        return estimated
