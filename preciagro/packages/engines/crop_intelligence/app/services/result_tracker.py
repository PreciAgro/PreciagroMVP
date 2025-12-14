from __future__ import annotations

from typing import Iterable, List

from ..core.metrics import (
    log_recommendation_batch,
    log_stage_estimate,
    track_action_decision,
)
from ..models.schemas import ActionOut, FeedbackIn, FieldStateOut


class ResultTracker:
    """Bridges user feedback into metrics + future learning datasets."""

    def log_recommendations(self, field_id: str, actions: List[ActionOut]) -> None:
        count = len(actions)
        if count:
            log_recommendation_batch(field_id, count)

    def log_feedback(self, feedback: FeedbackIn, action_type: str) -> None:
        acceptance = 1.0 if feedback.decision == "accepted" else 0.5 if feedback.decision == "modified" else 0.0
        track_action_decision(
            field_id=feedback.field_id,
            action_id=feedback.action_id,
            action_type=action_type or "unknown",
            decision=feedback.decision,
            confidence=acceptance,
            metadata={"note": feedback.note},
        )

    def log_stage_update(self, field_id: str, state: FieldStateOut) -> None:
        if state.stage is not None:
            log_stage_estimate(field_id, state.stage, state.stage_confidence)


result_tracker = ResultTracker()
