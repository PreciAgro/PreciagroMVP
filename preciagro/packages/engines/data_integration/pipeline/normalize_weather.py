# pipeline/normalize_weather.py
import hashlib
import json
import uuid
from datetime import datetime
from ..contracts.v1.normalized_item import NormalizedItem, Location


def to_normalized_weather(raw: dict, *, source_id: str) -> NormalizedItem:
    raw_bytes = json.dumps(raw, sort_keys=True).encode()
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    item_id = str(uuid.uuid5(uuid.NAMESPACE_URL,
                  f"{source_id}:{content_hash}"))

    # Adjust field names to your chosen weather API
    return NormalizedItem(
        item_id=item_id,
        source_id=source_id,
        collected_at=datetime.utcnow(),
        observed_at=datetime.fromisoformat(
            raw.get("time")) if raw.get("time") else None,
        kind="weather.forecast",
        location=Location(lat=raw.get("lat", 0.0), lon=raw.get(
            "lon", 0.0)) if raw.get("lat") else None,
        tags=["weather"],
        payload={"temp_c": raw.get("temp_c"), "humidity": raw.get("humidity")},
        raw_ref=None,
        content_hash=content_hash,
    )
