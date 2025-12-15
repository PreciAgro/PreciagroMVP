from __future__ import annotations

from typing import Dict, List

from ..models.schemas import FieldStateOut


class ExplanationService:
    """Produces plain-language rationales consumable by downstream NLP engines."""

    def status_explanation(
        self, field_id: str, state: FieldStateOut, rotation_hint: str | None, health_score: float
    ) -> List[str]:
        explanations = [
            f"Field {field_id} is currently in {state.stage or 'an early'} stage with vigor trend {state.vigor_trend or 'stable'}.",
            f"Confidence in stage estimate is {state.stage_confidence:.0%} and overall health score is {health_score:.0%}.",
        ]
        if rotation_hint:
            explanations.append(rotation_hint)
        return explanations

    def yield_explanation(self, features: Dict, p50: float) -> List[str]:
        drivers = sorted(
            ((k, abs(v)) for k, v in features.items() if isinstance(v, (int, float))),
            key=lambda item: item[1],
            reverse=True,
        )
        top = [f"{name}={features[name]}" for name, _ in drivers[:3]]
        return [
            f"Baseline yield expectation is {p50:.2f} t/ha.",
            "Top contributing signals: " + ", ".join(top) if top else "Signals not available.",
        ]

    def plan_explanation(self, plan_items: List[str]) -> List[str]:
        if not plan_items:
            return ["Plan currently holds only monitoring tasks."]
        return [
            "Upcoming focus areas: " + ", ".join(plan_items[:3]),
            "Temporal Logic slots ensure timing aligns with regional calendars.",
        ]


explanation_service = ExplanationService()
