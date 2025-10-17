from __future__ import annotations
from ..models.schemas import RiskCard


class HealthRisk:
    """Assesses disease and pest risks based on environmental conditions."""

    def disease_cards(self, rh: float | None, leaf_wet_hours: float | None, stage: str | None) -> list[RiskCard]:
        """Generate disease risk cards based on weather conditions.

        Args:
            rh: Relative humidity percentage
            leaf_wet_hours: Hours of leaf wetness
            stage: Current crop growth stage

        Returns:
            list: Disease risk cards
        """
        cards = []
        if rh and rh > 85 and (leaf_wet_hours or 0) > 10 and stage:
            cards.append(RiskCard(type="late_blight",
                         level="medium", confidence=0.6))
        return cards


hr = HealthRisk()
