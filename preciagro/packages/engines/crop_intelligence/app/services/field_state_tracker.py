from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session

from ..models.schemas import FieldStateOut, TelemetryBatch
from ..repos.state import FieldStateRepository
from ..repos.telemetry import TelemetryRepository
from .growth_stage_estimator import growth_stage_estimator
from .result_tracker import result_tracker


class FieldStateTracker:
    """Tracks field state including growth stage, vigor trends, and risks."""

    def update_with_telemetry(self, session: Session, tb: TelemetryBatch) -> FieldStateOut:
        """Update field state based on telemetry data and persist snapshot."""
        TelemetryRepository(session).record_batch(tb)
        prediction = growth_stage_estimator.predict(tb)
        vigor_trend = self._derive_vigor(tb)

        repo = FieldStateRepository(session)
        repo.update_stage(
            field_id=tb.field_id,
            stage_code=prediction.stage,
            stage_confidence=prediction.confidence,
            vigor_trend=vigor_trend,
            risks=None,
        )
        state = repo.as_schema(tb.field_id)
        result_tracker.log_stage_update(tb.field_id, state)
        return state

    def get(self, session: Session, field_id: str) -> FieldStateOut:
        """Get current field state from persistence."""
        return FieldStateRepository(session).as_schema(field_id)

    @staticmethod
    def _derive_vigor(tb: TelemetryBatch) -> Optional[str]:
        if tb.vi and len(tb.vi) >= 2:
            prev, curr = tb.vi[-2], tb.vi[-1]
            if curr.ndvi is not None and prev.ndvi is not None:
                delta = curr.ndvi - prev.ndvi
                if delta > 0.02:
                    return "increasing"
                if delta < -0.02:
                    return "decreasing"
                return "stable"
        return None


state_tracker = FieldStateTracker()
