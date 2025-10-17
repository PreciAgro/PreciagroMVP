from __future__ import annotations
from typing import Optional
from ..models.schemas import TelemetryBatch


class PhenologyWater:
    """Handles phenology stage estimation and water management recommendations."""

    def estimate_stage(self, tb: TelemetryBatch) -> tuple[Optional[str], float]:
        """Estimate crop growth stage from telemetry data.

        Returns:
            tuple: (stage_name, confidence_score)
        """
        # MVP heuristic: use EVI/NDVI thresholds to guess coarse stage
        if not tb.vi:
            return None, 0.0
        last = tb.vi[-1]
        ndvi = (last.ndvi or 0.0)
        if ndvi < 0.2:
            return "emergence", 0.5
        if ndvi < 0.5:
            return "vegetative", 0.6
        if ndvi < 0.75:
            return "reproductive", 0.6
        return "maturity", 0.5

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
