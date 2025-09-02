"""Core contracts and Pydantic models for Temporal Logic Engine."""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime

# Event coming from other engines (e.g., diagnosis)


class EngineEvent(BaseModel):
    # 'diagnosis.outcome', 'soil.moisture_update', ...
    topic: str
    id: str
    ts_utc: datetime
    farm_id: str
    farmer_tz: str
    payload: Dict[str, Any]


# === DSL types ===
Op = Literal["<", "<=", " >", ">=", "equals", "in", "not_in"]


class Clause(BaseModel):
    key: str
    op: Op
    value: Any


class Trigger(BaseModel):
    topic: str
    when: List[Clause] = []


class Preconditions(BaseModel):
    all: List[Clause] = []
    any: List[Clause] = []


class PreferredSubwindow(BaseModel):
    start_local: Optional[str] = None
    end_local: Optional[str] = None


class Window(BaseModel):
    start_offset_hours: Optional[int] = None
    end_offset_hours: Optional[int] = None
    start_at_local: Optional[str] = None
    end_at_local: Optional[str] = None
    day_offset: int = 0
    preferred_subwindow: Optional[PreferredSubwindow] = None


class Dedupe(BaseModel):
    scope: str
    ttl_hours: int = 24


class Message(BaseModel):
    short: str
    long: Optional[str] = None
    buttons: List[str] = []


class Rule(BaseModel):
    id: str
    version: int = 1
    trigger: Trigger
    preconditions: Preconditions = Preconditions()
    window: Window
    dedupe: Dedupe
    priority: Literal["low", "medium", "high"] = "medium"
    channels: List[Literal["whatsapp", "sms", "email", "push"]] = ["whatsapp"]
    message: Message

# API contracts


class TaskOutcomePost(BaseModel):
    outcome: Literal["done", "skipped"]
    note: Optional[str] = None
    evidence_url: Optional[str] = None
