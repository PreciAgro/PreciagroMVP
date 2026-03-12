"""Adapters that map Image Analysis responses into downstream engine payloads."""

from .adapters import (
    asdict_payload,
    to_crop_intelligence,
    to_data_integration,
    to_geo_context,
    to_temporal_logic,
)

__all__ = [
    "asdict_payload",
    "to_crop_intelligence",
    "to_temporal_logic",
    "to_geo_context",
    "to_data_integration",
]
