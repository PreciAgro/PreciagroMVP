# contracts/v1/normalized_item.py
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lon: float


class NormalizedItem(BaseModel):
    schema_version: Literal["v1"] = "v1"
    item_id: str  # deterministic UUID from source+hash
    source_id: str  # e.g. 'open-meteo'
    collected_at: datetime  # when *we* fetched it
    observed_at: Optional[datetime] = None  # when it happened
    kind: Literal["weather.observation", "weather.forecast", "market.price", "advisory"]
    location: Optional[Location] = None
    tags: List[str] = []
    payload: dict  # the useful fields (temp, humidity, etc.)
    raw_ref: Optional[str] = None  # where raw blob lives
    content_hash: str  # hash of raw payload for dedupe
