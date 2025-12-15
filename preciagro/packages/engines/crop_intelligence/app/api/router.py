from typing import List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..models.schemas import (
    FieldRegister,
    TelemetryBatch,
    PhotoIn,
    ActionLogIn,
    FieldStateOut,
    ActionOut,
    ActionsOut,
    FeedbackIn,
    FieldStatusResponse,
    YieldPredictIn,
    YieldPredictOut,
    RecommendActionsIn,
    ScheduleOut,
    ScheduleItem,
    CropStatusResponse,
    CropYieldRequest,
    CropYieldResponse,
    YieldScenarioResult,
    CropPlanRequest,
    CropPlanResponse,
    CropWindowsResponse,
    ExplainRequest,
    ExplainResponse,
)
from ..services.field_state_tracker import state_tracker
from ..services.learning_hooks import lh
from ..services.schedule_planner import planner
from ..services.action_recommender import action_recommender, ActionContext
from ..services.result_tracker import result_tracker
from ..services.yield_outlook import yo
from ..services.plan_builder import plan_builder
from ..services.window_service import window_service
from ..services.rotation import rotation_service
from ..services.explanations import explanation_service
from ..db import get_session, models
from ..repos.fields import FieldRepository
from ..repos.actions import ActionRepository
from ..repos.telemetry import TelemetryRepository
from ..integrations import integration_hub
from ..security.deps import require_service_token

router = APIRouter(prefix="/cie", tags=["CIE"], dependencies=[Depends(require_service_token)])
crop_router = APIRouter(
    prefix="/crop", tags=["Crop Intelligence"], dependencies=[Depends(require_service_token)]
)


@router.post("/field/register")
def register_field(
    payload: FieldRegister,
    db: Session = Depends(get_session),
) -> dict:
    """Register a new field with crop and management details.

    Args:
        payload: Field registration data

    Returns:
        Success confirmation
    """
    field = FieldRepository(db).upsert(payload)
    integration_hub.ensure_soil_baseline(TelemetryRepository(db), field)
    lh.emit("field_registered", payload.field_id, payload.model_dump())
    return {"ok": True}


@router.post("/field/telemetry")
def post_telemetry(
    tb: TelemetryBatch,
    db: Session = Depends(get_session),
) -> dict:
    """Submit telemetry data (weather, vegetation indices, soil) for a field.

    Args:
        tb: Telemetry batch data

    Returns:
        Success confirmation
    """
    state_tracker.update_with_telemetry(db, tb)
    lh.emit("telemetry", tb.field_id, tb.model_dump())
    return {"ok": True}


@router.get("/field/state")
def get_state(
    field_id: str,
    db: Session = Depends(get_session),
) -> FieldStateOut:
    """Get current field state including stage, vigor trend, and risks.

    Args:
        field_id: Field identifier

    Returns:
        Current field state
    """
    return state_tracker.get(db, field_id)


def _build_action_context(field_id: str, db: Session) -> Tuple[ActionContext, models.Field]:
    fields_repo = FieldRepository(db)
    tele_repo = TelemetryRepository(db)
    st = state_tracker.get(db, field_id)

    field = fields_repo.get(field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")

    whc = fields_repo.latest_soil_whc(field_id)
    season_features = tele_repo.season_summary(field_id)
    season_features.update(
        {
            "crop": field.crop,
            "whc_mm": whc or 0.0,
            "rain_forecast_mm": 12.0,
        }
    )

    ctx = ActionContext(
        field_id=field_id,
        field_repo=fields_repo,
        telemetry_repo=tele_repo,
        state=st,
        soil_whc=whc,
        season_features=season_features,
    )
    return ctx, field


def _build_actions(field_id: str, db: Session) -> list[ActionOut]:
    ctx, _ = _build_action_context(field_id, db)
    ranked = action_recommender.recommend(ctx)
    ActionRepository(db).persist_recommendations(field_id, ranked)
    result_tracker.log_recommendations(field_id, ranked)
    lh.emit("actions_proposed", field_id, {"count": len(ranked)})
    return ranked


@router.get("/field/actions")
def get_actions(
    field_id: str,
    db: Session = Depends(get_session),
) -> ActionsOut:
    ranked = _build_actions(field_id, db)
    return ActionsOut(items=ranked)


@router.post("/feedback")
def post_feedback(
    fb: FeedbackIn,
    db: Session = Depends(get_session),
) -> dict:
    """Submit farmer feedback on recommended actions.

    Args:
        fb: Feedback data including decision and notes

    Returns:
        Success confirmation
    """
    action_type = ActionRepository(db).record_feedback(fb)
    result_tracker.log_feedback(fb, action_type)
    lh.emit("feedback", fb.field_id, fb.model_dump())
    return {"ok": True}


@router.get("/status")
def field_status(
    field_id: str,
    db: Session = Depends(get_session),
) -> FieldStatusResponse:
    state = state_tracker.get(db, field_id)
    return FieldStatusResponse(field_id=field_id, state=state)


@router.post("/predict-yield")
def predict_yield(
    payload: YieldPredictIn,
    db: Session = Depends(get_session),
) -> YieldPredictOut:
    fields_repo = FieldRepository(db)
    tele_repo = TelemetryRepository(db)
    field = fields_repo.get(payload.field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    features = tele_repo.season_summary(payload.field_id)
    features.update(payload.season_features or {})
    features.setdefault("whc_mm", fields_repo.latest_soil_whc(payload.field_id) or 0.0)
    features.setdefault("crop", field.crop)
    p10, p50, p90, version = yo.p_bands(field.crop, features)
    return YieldPredictOut(
        field_id=payload.field_id, p10=p10, p50=p50, p90=p90, model_version=version
    )


@router.post("/recommend-actions")
def recommend_actions(
    payload: RecommendActionsIn,
    db: Session = Depends(get_session),
) -> ActionsOut:
    ranked = _build_actions(payload.field_id, db)
    return ActionsOut(items=ranked)


@router.get("/schedule")
def get_schedule(
    field_id: str,
    db: Session = Depends(get_session),
) -> ScheduleOut:
    state = state_tracker.get(db, field_id)
    schedule = planner.compose(field_id, state)
    external = integration_hub.fetch_schedule(field_id)
    if external and external.get("items"):
        for item in external["items"]:
            schedule.items.append(
                ScheduleItem(
                    task=item.get("task", "External Task"),
                    stage_hint=item.get("stage"),
                    earliest=item.get("earliest"),
                    latest=item.get("latest"),
                    notes=item.get("notes", []),
                )
            )
    return schedule


def _yield_result(name: str, crop: str, features: dict):
    p10, p50, p90, version = yo.p_bands(crop, features)
    drivers = sorted(
        ((k, abs(v)) for k, v in features.items() if isinstance(v, (int, float))),
        key=lambda item: item[1],
        reverse=True,
    )
    driver_text = [f"{key}={features[key]}" for key, _ in drivers[:3]]
    return name, p10, p50, p90, driver_text, version


@crop_router.get("/status")
def crop_status(
    field_id: str,
    db: Session = Depends(get_session),
) -> CropStatusResponse:
    ctx, field = _build_action_context(field_id, db)
    rotation = rotation_service.assess(field)
    state = ctx.state
    health_score = min(1.0, (rotation.health_score + (state.stage_confidence or 0)) / 2)
    return CropStatusResponse(
        field_id=field_id,
        stage=state.stage,
        health_score=health_score,
        confidence=state.stage_confidence or 0.0,
        vigor_trend=state.vigor_trend,
        rotation_hint=rotation.hint,
        risk_flags=rotation.risk_flags,
        last_update=None,
        explanations=explanation_service.status_explanation(
            field_id, state, rotation.hint, health_score
        ),
    )


@crop_router.post("/yield")
def crop_yield(
    payload: CropYieldRequest,
    db: Session = Depends(get_session),
) -> CropYieldResponse:
    ctx, field = _build_action_context(payload.field_id, db)
    features = ctx.season_features.copy()
    features.update(payload.baseline_features or {})
    name, p10, p50, p90, drivers, version = _yield_result("baseline", field.crop, features)
    baseline = YieldScenarioResult(name=name, p10=p10, p50=p50, p90=p90, delta=0.0, drivers=drivers)

    scenarios: List[YieldScenarioResult] = []
    for scenario in payload.scenarios:
        scenario_features = features.copy()
        scenario_features.update(scenario.adjustments or {})
        s_name, s_p10, s_p50, s_p90, s_drivers, _ = _yield_result(
            scenario.name, field.crop, scenario_features
        )
        scenarios.append(
            YieldScenarioResult(
                name=s_name,
                p10=s_p10,
                p50=s_p50,
                p90=s_p90,
                delta=s_p50 - baseline.p50,
                drivers=s_drivers,
            )
        )

    return CropYieldResponse(
        field_id=payload.field_id,
        baseline=baseline,
        scenarios=scenarios,
        model_version=version,
        explanations=explanation_service.yield_explanation(features, baseline.p50),
    )


@crop_router.post("/plan")
def crop_plan(
    payload: CropPlanRequest,
    db: Session = Depends(get_session),
) -> CropPlanResponse:
    ctx, field = _build_action_context(payload.field_id, db)
    schedule = planner.compose(payload.field_id, ctx.state)
    schedule_items = [item.model_dump() for item in schedule.items]
    actions = action_recommender.recommend(ctx)
    plan = plan_builder.build(
        payload.field_id, ctx.state, schedule_items, actions, payload.horizon_days
    )
    plan.explanations = explanation_service.plan_explanation([item.task for item in plan.items])
    return plan


@crop_router.get("/windows")
def crop_windows(
    crop: str,
    region: Optional[str] = None,
) -> CropWindowsResponse:
    windows = window_service.lookup(crop, region)
    return CropWindowsResponse(
        crop=crop,
        region=region,
        planting_window=windows["planting"],
        harvest_window=windows["harvest"],
        notes=["Derived from GeoContext baselines"],
    )


@crop_router.post("/explain")
def crop_explain(
    payload: ExplainRequest,
    db: Session = Depends(get_session),
) -> ExplainResponse:
    ctx, _ = _build_action_context(payload.field_id, db)
    explanations: List[str]
    if payload.topic == "yield":
        explanations = explanation_service.yield_explanation(
            ctx.season_features, ctx.season_features.get("expected_yield", 0)
        )
    elif payload.topic == "plan":
        schedule = planner.compose(payload.field_id, ctx.state)
        tasks = [item.task for item in schedule.items]
        explanations = explanation_service.plan_explanation(tasks)
    else:
        field = ctx.field_repo.get(payload.field_id)
        rotation = rotation_service.assess(field)
        explanations = explanation_service.status_explanation(
            payload.field_id, ctx.state, rotation.hint, rotation.health_score
        )
    return ExplainResponse(
        field_id=payload.field_id, topic=payload.topic, explanations=explanations
    )
