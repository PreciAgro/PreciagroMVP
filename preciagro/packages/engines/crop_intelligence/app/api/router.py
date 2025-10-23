from fastapi import APIRouter, HTTPException
from ..models.schemas import (
    FieldRegister, TelemetryBatch, PhotoIn, ActionLogIn,
    FieldStateOut, ActionOut, ActionsOut, FeedbackIn, RiskCard
)
from ..services.field_state_tracker import state_tracker
from ..services.phenology_water import pw
from ..services.nutrient_timing import nt
from ..services.health_risk import hr
from ..services.yield_outlook import yo
from ..services.decision_ranker import ranker
from ..services.learning_hooks import lh

router = APIRouter(prefix="/cie", tags=["CIE"])

_fields: dict[str, FieldRegister] = {}
_soil_cache: dict[str, float] = {}  # field_id -> whc_mm (approx)


@router.post("/field/register")
def register_field(payload: FieldRegister) -> dict:
    """Register a new field with crop and management details.

    Args:
        payload: Field registration data

    Returns:
        Success confirmation
    """
    _fields[payload.field_id] = payload
    lh.emit("field_registered", payload.field_id, payload.model_dump())
    return {"ok": True}


@router.post("/field/telemetry")
def post_telemetry(tb: TelemetryBatch) -> dict:
    """Submit telemetry data (weather, vegetation indices, soil) for a field.

    Args:
        tb: Telemetry batch data

    Returns:
        Success confirmation
    """
    state_tracker.update_with_telemetry(tb)
    if tb.soil and tb.soil.whc_mm:
        _soil = tb.soil.whc_mm
        _soil_cache[tb.field_id] = _soil
    lh.emit("telemetry", tb.field_id, tb.model_dump())
    return {"ok": True}


@router.get("/field/state")
def get_state(field_id: str) -> FieldStateOut:
    """Get current field state including stage, vigor trend, and risks.

    Args:
        field_id: Field identifier

    Returns:
        Current field state
    """
    # derive latest state snapshot
    st = state_tracker.get(field_id)
    # cheap stage estimate from last telemetry push (for MVP)
    # In a real service, store the last TelemetryBatch per field
    # Here we just return whatever we have
    return st


@router.get("/field/actions")
def get_actions(field_id: str) -> ActionsOut:
    """Get recommended actions for a field.

    Args:
        field_id: Field identifier

    Returns:
        Ranked list of recommended actions with explanations
    """
    # Get tracked state from telemetry (includes phenology estimate)
    st = state_tracker.get(field_id)
    stage, stage_conf = st.stage, st.stage_confidence

    # Get soil data from cache
    whc = _soil_cache.get(field_id)

    # Get water recommendations
    water = pw.water_need_message(whc_mm=whc, rain_forecast_mm=12)
    n_start, n_end, why_n = (None, None, [])
    if stage:
        n_start, n_end, why_n = nt.n_topdress_window(
            stage, rain_forecast_mm=12)

    cards: list[ActionOut] = []
    if "irrigate_mm" in water or "skip_if_rain_mm" in water:
        why = [f"stage={stage}"] + [f"soil_whc={whc or 'unknown'}"]
        if "skip_if_rain_mm" in water:
            why.append(f"skip if rain >= {water['skip_if_rain_mm']} mm")
        else:
            why.append(f"irrigate {water['irrigate_mm']} mm")
        cards.append(ActionOut(
            action_id=f"a_{field_id}_water",
            action="Water_Advisory",
            impact_score=0.7,
            why=why,
            uncertainty="medium",
        ))
    if n_start:
        cards.append(ActionOut(
            action_id=f"a_{field_id}_n",
            action="N_Topdress",
            impact_score=0.8,
            window_start=n_start,
            window_end=n_end,
            why=why_n,
            uncertainty="medium"
        ))
    # Disease card (placeholder)
    cards.append(ActionOut(
        action_id=f"a_{field_id}_scout",
        action="Scout_Disease",
        impact_score=0.5,
        when="tomorrow morning",
        why=["RH>85% for 12h", "Leaf-wetness proxy>10h"],
        uncertainty="low"
    ))

    ranked = ranker.rank(field_id, cards)
    lh.emit("actions_proposed", field_id, {"count": len(ranked)})
    return ActionsOut(items=ranked)


@router.post("/feedback")
def post_feedback(fb: FeedbackIn) -> dict:
    """Submit farmer feedback on recommended actions.

    Args:
        fb: Feedback data including decision and notes

    Returns:
        Success confirmation
    """
    lh.emit("feedback", fb.field_id, fb.model_dump())
    return {"ok": True}
