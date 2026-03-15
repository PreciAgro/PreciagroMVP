from pydantic import BaseModel, HttpUrl, field_validator
from typing import Literal


class AnalyzeRequest(BaseModel):
    image_url: str
    farmer_id: str
    message: str = ""

    @field_validator("image_url")
    @classmethod
    def image_url_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("image_url must not be empty")
        return v

    @field_validator("farmer_id")
    @classmethod
    def farmer_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("farmer_id must not be empty")
        return v


class AnalyzeResponse(BaseModel):
    insight: str
    action: str
    confidence: float
    confidence_reason: str
    urgency: Literal["low", "medium", "high", "critical"]
    follow_up: str
