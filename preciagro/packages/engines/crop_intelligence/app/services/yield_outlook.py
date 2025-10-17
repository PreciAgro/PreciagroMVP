from __future__ import annotations
from typing import Optional


class YieldOutlook:
    """Provides yield estimation and outlook based on season features."""

    def p_bands(self, season_features: dict) -> tuple[float, float, float]:
        """Calculate yield probability bands (P10, P50, P90).

        Args:
            season_features: Dictionary of season-level features

        Returns:
            tuple: (P10, P50, P90) yield estimates
        """
        # Placeholder: naive banding; replace with model
        p50 = season_features.get("cum_rain", 0) * 0.01 + 2.0
        return max(0.5, p50 - 0.7), p50, p50 + 0.7


yo = YieldOutlook()
