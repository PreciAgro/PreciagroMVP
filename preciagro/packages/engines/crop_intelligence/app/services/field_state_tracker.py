from __future__ import annotations
from typing import Optional, List
from ..models.schemas import FieldStateOut, RiskCard, TelemetryBatch
from .phenology_water import pw


class FieldStateTracker:
    """Tracks field state including growth stage, vigor trends, and risks."""

    def __init__(self):
        # naive in-memory state; swap to Redis/DB later
        self._state: dict[str, FieldStateOut] = {}

    def update_with_telemetry(self, tb: TelemetryBatch) -> None:
        """Update field state based on telemetry data.

        Pipes telemetry through phenology service to estimate growth stage,
        then stores the result in field state.
        """
        # Get or create state for this field
        st = self._state.get(tb.field_id, FieldStateOut(
            stage=None, stage_confidence=0.0))

        # Estimate stage using phenology service
        stage, stage_confidence = pw.estimate_stage(tb)
        st.stage = stage
        st.stage_confidence = stage_confidence

        # Derive a crude vigor trend from last two VI points
        if tb.vi and len(tb.vi) >= 2 and all(v.ndvi is not None for v in tb.vi[-2:]):
            prev, curr = tb.vi[-2], tb.vi[-1]
            if curr.ndvi is not None and prev.ndvi is not None:
                delta = curr.ndvi - prev.ndvi
                if delta > 0.02:
                    st.vigor_trend = "increasing"
                elif delta < -0.02:
                    st.vigor_trend = "decreasing"
                else:
                    st.vigor_trend = "stable"

        self._state[tb.field_id] = st

    def get(self, field_id: str) -> FieldStateOut:
        """Get current field state."""
        return self._state.get(field_id, FieldStateOut(stage=None, stage_confidence=0.0))


state_tracker = FieldStateTracker()
