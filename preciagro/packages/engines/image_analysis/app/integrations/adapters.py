"""Canonical adapters for downstream engines."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from ..models import ImageAnalysisResponse


@dataclass
class CropIntelligencePayload:
    crop: str
    disease_code: str
    stage_code: str
    health_score: float
    lesion_area_pct: Optional[float]
    uncertain: bool
    explanations: Dict[str, Optional[str]]


@dataclass
class TemporalLogicPayload:
    field_id: Optional[str]
    crop: str
    stage_code: str
    next_check_hours: int
    notes: list[str]


@dataclass
class GeoContextPayload:
    field_id: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    captured_at: Optional[str]
    disease_code: str
    health_score: float


@dataclass
class DataIntegrationPayload:
    raw: Dict[str, Any]
    artifacts: Dict[str, Optional[str]]


def to_crop_intelligence(resp: ImageAnalysisResponse) -> CropIntelligencePayload:
    return CropIntelligencePayload(
        crop=resp.crop,
        disease_code=resp.disease.code,
        stage_code=resp.growth_stage.code,
        health_score=resp.health_score,
        lesion_area_pct=resp.lesion_area_pct,
        uncertain=not resp.quality.passed,
        explanations={
            "gradcam": resp.explanations.gradcam_url,
            "mask_overlay": resp.explanations.mask_url,
            "mask_binary": resp.explanations.mask_binary_url,
        },
    )


def to_temporal_logic(resp: ImageAnalysisResponse) -> TemporalLogicPayload:
    next_check = 24
    if not resp.quality.passed:
        next_check = 6
    elif resp.health_score < 0.5:
        next_check = 12

    notes = list(resp.quality.notes)
    if resp.lesion_area_pct and resp.lesion_area_pct > 0.25:
        notes.append("High lesion coverage detected; escalate to agronomist.")

    return TemporalLogicPayload(
        field_id=resp.meta.field_id,
        crop=resp.crop,
        stage_code=resp.growth_stage.code,
        next_check_hours=next_check,
        notes=notes,
    )


def to_geo_context(resp: ImageAnalysisResponse) -> GeoContextPayload:
    return GeoContextPayload(
        field_id=resp.meta.field_id,
        lat=resp.meta.lat,
        lon=resp.meta.lon,
        captured_at=resp.meta.captured_at.isoformat() if resp.meta.captured_at else None,
        disease_code=resp.disease.code,
        health_score=resp.health_score,
    )


def to_data_integration(resp: ImageAnalysisResponse) -> DataIntegrationPayload:
    raw = resp.model_dump()
    artifacts = {
        "gradcam": resp.explanations.gradcam_url,
        "mask_overlay": resp.explanations.mask_url,
        "mask_binary": resp.explanations.mask_binary_url,
    }
    return DataIntegrationPayload(raw=raw, artifacts=artifacts)


def asdict_payload(payload) -> Dict[str, Any]:
    """Helper for tests and JSON serialization."""

    return asdict(payload)
