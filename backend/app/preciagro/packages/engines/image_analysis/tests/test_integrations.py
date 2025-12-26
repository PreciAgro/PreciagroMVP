from __future__ import annotations

from datetime import datetime

from preciagro.packages.engines.image_analysis.app.integrations import (
    asdict_payload,
    to_crop_intelligence,
    to_data_integration,
    to_geo_context,
    to_temporal_logic,
)
from preciagro.packages.engines.image_analysis.app.models import (
    AnalysisMetadata,
    CountsResult,
    DiseasePrediction,
    GrowthStagePrediction,
    ImageAnalysisResponse,
    ImageQualityResult,
    ResponseExplanations,
)


def _response() -> ImageAnalysisResponse:
    return ImageAnalysisResponse(
        crop="maize",
        disease=DiseasePrediction(code="CIE.DZ.GRAY_LEAF_SPOT", label="gls", conf=0.8),
        growth_stage=GrowthStagePrediction(
            code="STAGE.VEGETATIVE",
            label="vegetative",
            conf=0.7,
        ),
        health_score=0.72,
        lesion_area_pct=0.2,
        counts=CountsResult(fruit=3, pest=1),
        quality=ImageQualityResult(passed=False, notes=["blur"]),
        explanations=ResponseExplanations(
            gradcam_url="https://cdn/gcam.png",
            mask_url="https://cdn/mask.png",
            mask_binary_url="https://cdn/mask.bin.png",
        ),
        meta=AnalysisMetadata(
            field_id="field-123",
            lat=10.2,
            lon=20.5,
            captured_at=datetime(2025, 1, 1),
        ),
    )


def test_crop_intelligence_adapter() -> None:
    payload = to_crop_intelligence(_response())
    data = asdict_payload(payload)
    assert data["disease_code"] == "CIE.DZ.GRAY_LEAF_SPOT"
    assert data["uncertain"] is True
    assert str(data["explanations"]["mask_binary"]).endswith("mask.bin.png")


def test_temporal_logic_adapter() -> None:
    payload = to_temporal_logic(_response())
    assert payload.next_check_hours == 6
    assert "blur" in payload.notes


def test_geo_context_adapter() -> None:
    payload = to_geo_context(_response())
    assert payload.lat == 10.2
    assert payload.captured_at.startswith("2025-01-01")


def test_data_integration_adapter_contains_artifacts() -> None:
    payload = to_data_integration(_response())
    assert str(payload.artifacts["gradcam"]).endswith("gcam.png")
    assert payload.raw["counts"]["fruit"] == 3
