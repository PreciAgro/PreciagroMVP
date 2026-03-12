# pipeline/normalize_openweather.py
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Literal

from ..contracts.v1.normalized_item import Location, NormalizedItem


def _ts(dt_unix: int | None):
    """Convert Unix timestamp (seconds) to UTC datetime or return None.

    TODO: handle millisecond timestamps if we start ingesting other providers.
    """
    if dt_unix is None:
        return None
    return datetime.fromtimestamp(dt_unix, tz=timezone.utc)


def _hash(raw: Dict[str, Any]) -> str:
    """Compute a stable SHA-256 hex digest for the given raw dict.

    We JSON-serialize with sort_keys=True to ensure deterministic ordering. The
    default=str is used to avoid serialization errors for unexpected types;
    if you need strictness, validate upstream and remove default=str.
    """
    raw_bytes = json.dumps(raw, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw_bytes).hexdigest()


def normalize_openweather(
    raw: Dict[str, Any],
    *,
    source_id: str,
    kind: Literal["weather.observation", "weather.forecast"],
) -> NormalizedItem:
    """Normalize OpenWeather raw record into `NormalizedItem`.

    The normalizer hides provider-specific field names and shapes and returns a
    stable contract for downstream engines to consume. It must set
    `content_hash` so de-duplication is deterministic.

    TODOs:
    - Add mapping for additional providers and a registry to choose mapper by
      provider id.
    - Consider a richer payload schema (units, confidence, etc.).
    """

    # coordinates
    lat = raw.get("lat")
    lon = raw.get("lon")

    # timestamps
    observed_at = _ts(raw.get("dt"))

    # temp & humidity differences by scope:
    # - current/hourly: temp is a float (°C), humidity is int
    # - daily: temp is dict {day,min,max}; no humidity sometimes
    temp_c = None
    humidity = raw.get("humidity")
    weather_arr = raw.get("weather") or []
    description = weather_arr[0]["description"] if weather_arr else None

    if isinstance(raw.get("temp"), (int, float)):
        temp_c = raw["temp"]
    elif isinstance(raw.get("temp"), dict):
        # daily block: choose day avg as canonical temp
        temp_c = raw["temp"].get("day")

    payload = {
        "provider": "openweather",
        "description": description,
        "temp_c": temp_c,
        "humidity": humidity,
    }

    # content hash from raw (stable id)
    content_hash = _hash(raw)
    item_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{content_hash}"))

    return NormalizedItem(
        item_id=item_id,
        source_id=source_id,
        collected_at=datetime.now(timezone.utc),
        observed_at=observed_at,
        kind=kind,
        location=(Location(lat=lat, lon=lon) if (lat is not None and lon is not None) else None),
        tags=["weather", "openweather"],
        payload=payload,
        raw_ref=None,
        content_hash=content_hash,
    )
