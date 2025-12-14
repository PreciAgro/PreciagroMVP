from __future__ import annotations

from sqlalchemy.orm import Session

from ..db import models
from ..models.schemas import FeedbackIn, ActionOut


class ActionRepository:
    """Persists recommendations and farmer feedback."""

    def __init__(self, session: Session):
        self.session = session

    def persist_recommendations(self, field_id: str, actions: list[ActionOut]) -> None:
        for action in actions:
            record = models.Recommendation(
                id=action.action_id,
                field_id=field_id,
                action=action.action,
                payload=action.model_dump(),
                stage_code=None,
                source="heuristic",
                impact_score=action.impact_score,
            )
            self.session.merge(record)

    def record_feedback(self, fb: FeedbackIn) -> str:
        action_type = "unknown"
        recommendation = self.session.get(models.Recommendation, fb.action_id)
        if recommendation:
            action_type = recommendation.action
        entry = models.ActionFeedback(
            recommendation_id=fb.action_id,
            field_id=fb.field_id,
            action_id=fb.action_id,
            decision=fb.decision,
            note=fb.note,
        )
        self.session.add(entry)
        return action_type
