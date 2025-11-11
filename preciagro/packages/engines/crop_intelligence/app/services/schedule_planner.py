from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from ..models.schemas import FieldStateOut, ScheduleItem, ScheduleOut


class SchedulePlanner:
    """Produces lightweight task timelines until Temporal Logic integration lands."""

    def compose(self, field_id: str, state: FieldStateOut) -> ScheduleOut:
        now = datetime.utcnow()
        items: List[ScheduleItem] = []

        if state.stage:
            items.append(
                ScheduleItem(
                    task="Stage Review",
                    stage_hint=state.stage,
                    earliest=now.isoformat(),
                    latest=(now + timedelta(days=2)).isoformat(),
                    notes=[f"stage_confidence={state.stage_confidence:.2f}"],
                )
            )

        items.append(
            ScheduleItem(
                task="Telemetry Sync",
                stage_hint=state.stage,
                earliest=(now + timedelta(days=1)).isoformat(),
                latest=(now + timedelta(days=3)).isoformat(),
                notes=["Ensure weather + VI feeds are up to date"],
            )
        )

        return ScheduleOut(field_id=field_id, items=items)


planner = SchedulePlanner()
