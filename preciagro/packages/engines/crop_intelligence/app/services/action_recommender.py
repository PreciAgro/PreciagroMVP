from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..models.schemas import ActionOut, FieldStateOut
from ..repos.fields import FieldRepository
from ..repos.telemetry import TelemetryRepository
from .phenology_water import pw
from .nutrient_timing import nt
from .yield_outlook import yo
from .decision_ranker import ranker


@dataclass
class ActionContext:
    field_id: str
    field_repo: FieldRepository
    telemetry_repo: TelemetryRepository
    state: FieldStateOut
    soil_whc: Optional[float]
    season_features: dict


class ActionRecommender:
    """Central place to generate and rank action cards."""

    def recommend(self, ctx: ActionContext) -> List[ActionOut]:
        cards: List[ActionOut] = []
        stage = ctx.state.stage

        water = pw.water_need_message(ctx.soil_whc, ctx.season_features.get("rain_forecast_mm"))
        if "irrigate_mm" in water or "skip_if_rain_mm" in water:
            why = [
                f"stage={stage or 'unknown'}",
                f"soil_whc={ctx.soil_whc or 'n/a'}",
            ]
            if "skip_if_rain_mm" in water:
                why.append(f"rain_forecast>= {water['skip_if_rain_mm']} mm")
            else:
                why.append(f"apply {water['irrigate_mm']} mm")
            cards.append(
                ActionOut(
                    action_id=f"{ctx.field_id}_water",
                    action="Water_Advisory",
                    impact_score=0.7,
                    why=why,
                    uncertainty="medium",
                )
            )

        if stage:
            n_start, n_end, why_n = nt.n_topdress_window(
                stage, rain_forecast_mm=ctx.season_features.get("rain_forecast_mm", 0)
            )
            if n_start:
                cards.append(
                    ActionOut(
                        action_id=f"{ctx.field_id}_n",
                        action="N_Topdress",
                        impact_score=0.8,
                        window_start=n_start,
                        window_end=n_end,
                        why=why_n,
                        uncertainty="medium",
                    )
                )

        crop = ctx.season_features.get("crop")
        p10, p50, p90, _ = yo.p_bands(crop, ctx.season_features)
        cards.append(
            ActionOut(
                action_id=f"{ctx.field_id}_yield",
                action="Yield_Outlook",
                impact_score=0.4,
                why=[f"P50={p50:.2f} t/ha", f"range=({p10:.2f}-{p90:.2f})"],
                uncertainty="medium",
            )
        )

        return ranker.rank(ctx.field_id, cards)


action_recommender = ActionRecommender()
