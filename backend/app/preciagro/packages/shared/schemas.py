
from pydantic import BaseModel, Field
from typing import List, Optional

class GeoPoint(BaseModel):
    lat: float
    lng: float

class ImageIn(BaseModel):
    image_base64: str
    crop_hint: Optional[str] = None
    location: Optional[GeoPoint] = None

class LabelScore(BaseModel):
    name: str
    score: float

class DiagnosisOut(BaseModel):
    labels: List[LabelScore]
    notes: str
    model_version: str

class TaskItem(BaseModel):
    day_offset: int
    title: str
    instructions: str

class ActionPlan(BaseModel):
    crop: str
    diagnosis_label: str
    rationale: str
    tasks: List[TaskItem] = []

class Reminder(BaseModel):
    in_hours: int
    message: str

class PlanResponse(BaseModel):
    diagnosis: DiagnosisOut
    plan: ActionPlan
    reminders: List[Reminder]
    inventory: dict
