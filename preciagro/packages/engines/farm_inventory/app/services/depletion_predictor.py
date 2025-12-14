"""Service for predicting inventory depletion."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from ..repos.inventory import InventoryRepository
from ..repos.usage import UsageLogRepository
from ..models.schemas import DepletionPredictionResponse


class DepletionPredictor:
    """Predicts when inventory items will run out based on usage patterns."""

    def __init__(
        self,
        inventory_repo: InventoryRepository,
        usage_repo: UsageLogRepository,
    ):
        self.inventory_repo = inventory_repo
        self.usage_repo = usage_repo

    def predict_depletion(
        self,
        item_id: str,
        lookback_days: int = 7,
    ) -> Optional[DepletionPredictionResponse]:
        """Predict when an item will run out.
        
        Uses rule-based estimation:
        - Calculates average daily usage from historical logs
        - Estimates remaining days = current_quantity / estimated_daily_usage
        """
        item = self.inventory_repo.get_by_id(item_id)
        if not item or item.quantity <= 0:
            return None

        # Calculate average daily usage
        daily_usage = self.usage_repo.calculate_usage_rate(item_id, days=lookback_days)
        
        if daily_usage is None or daily_usage == 0:
            # No usage history - cannot predict
            return DepletionPredictionResponse(
                item_id=item_id,
                item_name=item.name,
                current_quantity=item.quantity,
                unit=item.unit,
                estimated_daily_usage=Decimal("0.00"),
                estimated_depletion_days=None,
                confidence=0.0,
                prediction_basis="No usage history available",
            )

        # Calculate days until depletion
        if daily_usage > 0:
            days_until_depletion = int(item.quantity / daily_usage)
        else:
            days_until_depletion = None

        # Confidence based on amount of historical data
        # More days of history = higher confidence
        confidence = min(1.0, lookback_days / 30.0)  # Max confidence at 30 days

        basis = (
            f"Based on {lookback_days} days of usage history. "
            f"Average daily usage: {daily_usage:.2f} {item.unit}"
        )

        return DepletionPredictionResponse(
            item_id=item_id,
            item_name=item.name,
            current_quantity=item.quantity,
            unit=item.unit,
            estimated_daily_usage=daily_usage,
            estimated_depletion_days=days_until_depletion,
            confidence=confidence,
            prediction_basis=basis,
        )

    def predict_depletion_with_crop_context(
        self,
        item_id: str,
        crop_type: str,
        crop_stage: str,
        field_size_ha: float,
        lookback_days: int = 7,
    ) -> Optional[DepletionPredictionResponse]:
        """Predict depletion with crop-specific context.
        
        This method can incorporate agronomic rules for better predictions.
        For MVP, we use basic usage rate, but this can be enhanced with:
        - Crop-specific usage rates per growth stage
        - Field size adjustments
        - Seasonal factors
        """
        # For MVP, use basic prediction
        # In production, this would incorporate:
        # - Crop-specific usage rates from Crop Intelligence Engine
        # - Growth stage multipliers
        # - Field size adjustments
        
        base_prediction = self.predict_depletion(item_id, lookback_days)
        if not base_prediction:
            return None

        # Apply crop stage multiplier (simplified for MVP)
        # In production, get these from Crop Intelligence Engine
        stage_multipliers = {
            "planting": 1.0,
            "vegetative": 1.5,
            "flowering": 2.0,
            "fruiting": 1.8,
            "maturity": 0.5,
        }
        
        multiplier = stage_multipliers.get(crop_stage.lower(), 1.0)
        adjusted_daily_usage = base_prediction.estimated_daily_usage * Decimal(str(multiplier))
        
        item = self.inventory_repo.get_by_id(item_id)
        if not item:
            return None

        if adjusted_daily_usage > 0:
            days_until_depletion = int(item.quantity / adjusted_daily_usage)
        else:
            days_until_depletion = None

        basis = (
            f"{base_prediction.prediction_basis}. "
            f"Adjusted for {crop_stage} stage (multiplier: {multiplier:.2f})"
        )

        return DepletionPredictionResponse(
            item_id=base_prediction.item_id,
            item_name=base_prediction.item_name,
            current_quantity=base_prediction.current_quantity,
            unit=base_prediction.unit,
            estimated_daily_usage=adjusted_daily_usage,
            estimated_depletion_days=days_until_depletion,
            confidence=min(0.8, base_prediction.confidence),  # Slightly lower due to estimation
            prediction_basis=basis,
        )

