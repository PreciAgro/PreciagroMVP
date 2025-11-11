from __future__ import annotations
from typing import Optional
from ..models.schemas import TelemetryBatch


class PhenologyWater:
    """Water advisory helper; stage estimation handled by GrowthStageEstimator."""

    def water_need_message(self, whc_mm: Optional[float], rain_forecast_mm: Optional[float]) -> dict:
        """Calculate water management recommendations.

        Args:
            whc_mm: Water holding capacity in mm
            rain_forecast_mm: Forecasted rainfall in mm

        Returns:
            dict: Water management advice
        """
        # Very simple placeholder; replace with FAO-56 ETc in next sprint
        advice = {}
        if whc_mm is None:
            return {"note": "insufficient soil data"}
        if rain_forecast_mm and rain_forecast_mm >= 15:
            advice["skip_if_rain_mm"] = 15
        else:
            advice["irrigate_mm"] = 18
        return advice


pw = PhenologyWater()
