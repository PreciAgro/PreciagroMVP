"""Utilities to redact sensitive fields before logging."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

SENSITIVE_KEYS = {
    "user",
    "user_id",
    "farm_ids",
    "location",
    "lat",
    "lon",
    "latitude",
    "longitude",
    "attachments",
}


def sanitize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a redacted copy of the payload."""
    sanitized = deepcopy(data)
    for key in list(sanitized.keys()):
        if key in ("user",):
            sanitized[key] = "<redacted>"
        elif key in ("farm_ids",):
            sanitized[key] = ["<redacted>"]
        elif key in ("lat", "lon", "latitude", "longitude"):
            sanitized[key] = "<redacted>"
        elif key.lower() in SENSITIVE_KEYS:
            sanitized[key] = "<redacted>"
    # redact nested metadata if present
    metadata = sanitized.get("metadata")
    if isinstance(metadata, dict):
        for k in list(metadata.keys()):
            if k in SENSITIVE_KEYS:
                metadata[k] = "<redacted>"
    # attachments: keep count only
    if "attachments" in sanitized and isinstance(sanitized["attachments"], list):
        sanitized["attachments"] = f"{len(sanitized['attachments'])} attachment(s) redacted"
    return sanitized
