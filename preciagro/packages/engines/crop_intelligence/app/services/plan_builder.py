from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from ..models.schemas import CropPlanItem, CropPlanResponse, FieldStateOut, ActionOut


class PlanBuilder:
    """Compose crop plans for the next horizon window."""

    def build(self, field_id: str, state: FieldStateOut, schedule_items: List[dict], actions: List[ActionOut], horizon_days: int) -> CropPlanResponse:
        items: List[CropPlanItem] = []
        now = datetime.utcnow()

        for schedule in schedule_items:
            items.append(
                CropPlanItem(
                    task=schedule.get("task", "Scheduled Task"),
                    stage_hint=schedule.get("stage_hint") or state.stage,
                    start_at=schedule.get("earliest"),
                    end_at=schedule.get("latest"),
                    sources=["temporal_logic"],
                    rationale=schedule.get("notes", []),
                )
            )

        for action in actions:
            start_at = action.window_start
            if not start_at and action.when:
                start_at = f"{action.when}"
            if not start_at:
                start_at = (now).isoformat()
            end_at = action.window_end or (now + timedelta(days=7)).isoformat()
            items.append(
                CropPlanItem(
                    task=action.action,
                    stage_hint=state.stage,
                    start_at=start_at,
                    end_at=end_at,
                    sources=["action_recommender"],
                    rationale=action.why or [],
                )
            )

        filtered = items[:]
        return CropPlanResponse(field_id=field_id, horizon_days=horizon_days, items=filtered, explanations=[])


plan_builder = PlanBuilder()
