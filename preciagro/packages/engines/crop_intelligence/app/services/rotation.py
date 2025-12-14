from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..db import models


@dataclass
class RotationAssessment:
    hint: Optional[str]
    risk_flags: List[str]
    health_score: float


class RotationService:
    """Very lightweight rotation heuristics until agronomy engine is wired."""

    def assess(self, field: models.Field) -> RotationAssessment:
        crop = (field.crop or "").lower()
        risk_flags: List[str] = []
        hint: Optional[str] = None
        base_health = 0.7

        if crop == "maize":
            hint = "Consider rotating with legumes (soybean, groundnut) after this season to replenish nitrogen."
            risk_flags.append("nitrogen_depletion")
        elif crop in {"wheat", "barley"}:
            hint = "Rotate with a broadleaf crop to break cereal disease cycles."
            risk_flags.append("disease_carryover")
        elif crop == "potato":
            hint = "Avoid planting potato on the same field within 3 years to limit late blight risk."
            risk_flags.append("soil_pathogen_pressure")

        health_score = max(0.3, base_health - 0.05 * len(risk_flags))
        return RotationAssessment(hint=hint, risk_flags=risk_flags, health_score=health_score)


rotation_service = RotationService()
