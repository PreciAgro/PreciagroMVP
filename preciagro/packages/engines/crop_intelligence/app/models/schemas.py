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
