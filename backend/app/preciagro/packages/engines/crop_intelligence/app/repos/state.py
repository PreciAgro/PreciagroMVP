from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..db import models
from ..models.schemas import FieldStateOut, RiskCard


class FieldStateRepository:
    """Handles persistence of derived field state snapshots."""

    def __init__(self, session: Session):
        self.session = session

    def get_or_create(self, field_id: str) -> models.FieldState:
        state = self.session.get(models.FieldState, field_id)
        if state is None:
            state = models.FieldState(field_id=field_id, stage_confidence=0.0)
            self.session.add(state)
            self.session.flush()
        return state

    def update_stage(
        self,
        field_id: str,
        stage_code: Optional[str],
        stage_confidence: float,
        vigor_trend: Optional[str],
        risks: Optional[list[RiskCard]] = None,
        last_telemetry_ts: Optional[datetime] = None,
    ) -> models.FieldState:
        state = self.get_or_create(field_id)
        state.stage_code = stage_code
        state.stage_confidence = stage_confidence
        state.vigor_trend = vigor_trend
        state.risks = [card.model_dump() for card in risks] if risks else None
        if last_telemetry_ts:
            state.last_telemetry_ts = last_telemetry_ts
        return state

    def as_schema(self, field_id: str) -> FieldStateOut:
        state = self.get_or_create(field_id)
        risks = []
        if state.risks:
            risks = [RiskCard(**item) for item in state.risks]
        return FieldStateOut(
            stage=state.stage_code,
            stage_confidence=state.stage_confidence or 0.0,
            vigor_trend=state.vigor_trend,
            risks=risks,
        )
