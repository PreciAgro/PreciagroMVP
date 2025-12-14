from typing import List, Optional, Literal
from pydantic import BaseModel, Field

BudgetClass = Literal["low", "medium", "high"]
IrrigationAccess = Literal["none", "limited", "full"]


class FieldRegister(BaseModel):
    field_id: str
    boundary_geojson: dict
    crop: str
    variety: Optional[str] = None
    planting_date: Optional[str] = None  # ISO date
    irrigation_access: IrrigationAccess = "none"
    target_yield_band: Optional[str] = None
    budget_class: BudgetClass = "low"


class WeatherPoint(BaseModel):
    ts: str
    tmax: float
    tmin: float
    rh: Optional[float] = None
    wind: Optional[float] = None
    rad: Optional[float] = None
    rain: float


class VIPoint(BaseModel):
    date: str
    ndvi: Optional[float] = None
    evi: Optional[float] = None
    quality: Literal["good", "cloudy", "gap"] = "good"


class SoilBaseline(BaseModel):
    src: str = "soilgrids"
    texture: Optional[str] = None
    whc_mm: Optional[float] = None
    uncertainty: Optional[str] = None


class TelemetryBatch(BaseModel):
    field_id: str
    weather: Optional[List[WeatherPoint]] = None
    vi: Optional[List[VIPoint]] = None
    soil: Optional[SoilBaseline] = None


class PhotoIn(BaseModel):
    field_id: str
    stage_hint: Optional[str] = None
    uri: str


class ActionLogIn(BaseModel):
    field_id: str
    date: str
    action: str
    subtype: Optional[str] = None
    amount_kg: Optional[float] = None


class RiskCard(BaseModel):
    type: str
    level: Literal["low", "medium", "high"]
    confidence: float


class FieldStateOut(BaseModel):
    stage: Optional[str]
    stage_confidence: float = 0.0
    vigor_trend: Optional[Literal["increasing", "stable", "decreasing"]] = None
    risks: List[RiskCard] = Field(default_factory=list)


class ActionOut(BaseModel):
    action_id: str
    action: str
    impact_score: float
    why: List[str]
    alternatives: List[str] = Field(default_factory=list)
    uncertainty: Literal["low", "medium", "high"] = "medium"
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    when: Optional[str] = None
    cost_hint: Optional[str] = None


class ActionsOut(BaseModel):
    items: List[ActionOut]


class FeedbackIn(BaseModel):
    field_id: str
    action_id: str
    decision: Literal["accepted", "modified", "ignored"]
    note: Optional[str] = None


class CropStatusResponse(BaseModel):
    field_id: str
    stage: Optional[str]
    health_score: float
    confidence: float
    vigor_trend: Optional[str] = None
    rotation_hint: Optional[str] = None
    risk_flags: List[str] = Field(default_factory=list)
    last_update: Optional[str] = None
    explanations: List[str] = Field(default_factory=list)


class YieldScenario(BaseModel):
    name: str
    adjustments: dict = Field(default_factory=dict)


class YieldScenarioResult(BaseModel):
    name: str
    p10: float
    p50: float
    p90: float
    delta: float
    drivers: List[str] = Field(default_factory=list)


class CropYieldRequest(BaseModel):
    field_id: str
    baseline_features: dict = Field(default_factory=dict)
    scenarios: List[YieldScenario] = Field(default_factory=list)


class CropYieldResponse(BaseModel):
    field_id: str
    baseline: YieldScenarioResult
    scenarios: List[YieldScenarioResult] = Field(default_factory=list)
    model_version: str
    explanations: List[str] = Field(default_factory=list)


class CropPlanRequest(BaseModel):
    field_id: str
    horizon_days: int = 21
    strategy: Optional[str] = None


class CropPlanItem(BaseModel):
    task: str
    stage_hint: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    rationale: List[str] = Field(default_factory=list)


class CropPlanResponse(BaseModel):
    field_id: str
    horizon_days: int
    items: List[CropPlanItem]
    explanations: List[str] = Field(default_factory=list)


class CropWindowsResponse(BaseModel):
    crop: str
    region: Optional[str]
    planting_window: List[str]
    harvest_window: List[str]
    notes: List[str] = Field(default_factory=list)


class ExplainRequest(BaseModel):
    field_id: str
    topic: Literal["status", "yield", "plan"] = "status"
    context: dict = Field(default_factory=dict)


class ExplainResponse(BaseModel):
    field_id: str
    topic: str
    explanations: List[str]


class FieldStatusResponse(BaseModel):
    field_id: str
    state: FieldStateOut


class YieldPredictIn(BaseModel):
    field_id: str
    season_features: dict = Field(default_factory=dict)


class YieldPredictOut(BaseModel):
    field_id: str
    p10: float
    p50: float
    p90: float
    model_version: str = "heuristic_v0"


class RecommendActionsIn(BaseModel):
    field_id: str
    constraints: Optional[dict] = None


class ScheduleItem(BaseModel):
    task: str
    stage_hint: Optional[str] = None
    earliest: Optional[str] = None
    latest: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class ScheduleOut(BaseModel):
    field_id: str
    items: List[ScheduleItem] = Field(default_factory=list)
