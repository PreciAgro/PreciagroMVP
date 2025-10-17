from __future__ import annotations
from typing import Optional

class NutrientTiming:
    """Manages nutrient application timing recommendations."""
    
    def n_topdress_window(self, stage: Optional[str], rain_forecast_mm: Optional[float]) -> tuple[Optional[str], Optional[str], list[str]]:
        """Determine optimal nitrogen top-dress window.
        
        Args:
            stage: Current crop growth stage
            rain_forecast_mm: Forecasted rainfall in mm
            
        Returns:
            tuple: (window_start, window_end, reasoning)
        """
        why = []
        if stage in {"vegetative"}:
            why.append("vegetative stage: N demand rising")
            if rain_forecast_mm and rain_forecast_mm >= 10:
                why.append("rain window ≥10mm")
                return ("soon", "+3d", why)
            return ("soon", "+7d", why)
        return (None, None, ["stage not optimal for N top-dress"]) 

nt = NutrientTiming()
