from __future__ import annotations

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from preciagro.packages.engines.image_analysis.app.core.registry import (
    ClassifierConfig,
    CropModelConfig,
)
from preciagro.packages.engines.image_analysis.app.inference.classifier import (
    ClassifierHead,
)
from preciagro.packages.engines.image_analysis.app.models import ImageAnalysisRequest
from preciagro.packages.shared.schemas import DiagnosisOut, LabelScore


def _make_crop_config() -> CropModelConfig:
    return CropModelConfig(
        classifier=ClassifierConfig(
            name="efficientnet_v2_s", weights_path="", threshold=0.6, top_k=2, tta=False
        ),
    )


def test_load_model_reuses_cached_backbone(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated loads for the same crop config should hit the cache and avoid re-instantiating timm."""

    from preciagro.packages.engines.image_analysis.app.inference import classifier as module

    dummy_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)),
    )
    monkeypatch.setattr(module, "torch", dummy_torch)

    mock_model = MagicMock()
    mock_model.eval.return_value = mock_model
    mock_model.to.return_value = mock_model
    mock_model.pretrained_cfg = {"label_names": ["gray_leaf_spot", "rust"]}

    create_model_mock = MagicMock(return_value=mock_model)
    monkeypatch.setattr(module, "create_model", create_model_mock)
    monkeypatch.setattr(module, "resolve_data_config", lambda *_, **__: {})
    monkeypatch.setattr(module, "create_transform", lambda **kwargs: lambda img: img)

    head = ClassifierHead()
    crop_config = _make_crop_config()

    bundle_one = head._load_model(crop_config)
    bundle_two = head._load_model(crop_config)

    assert bundle_one is bundle_two
    assert create_model_mock.call_count == 1
    assert bundle_one["class_names"] == ["gray_leaf_spot", "rust"]


def test_predict_falls_back_to_stub_when_timm_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """If torch/timm are unavailable the classifier head should rely on the heuristic diagnose stub."""

    from preciagro.packages.engines.image_analysis.app.inference import classifier as module

    diagnosis = DiagnosisOut(
        labels=[LabelScore(name="leaf_spot", score=0.61)],
        notes="stub",
        model_version="stub-0.2",
    )
    monkeypatch.setattr(module, "diagnose", lambda *_: diagnosis)
    monkeypatch.setattr(ClassifierHead, "_timm_available", lambda self: False)

    payload = ImageAnalysisRequest(
        crop="maize",
        image_base64=base64.b64encode(b"stub").decode(),
    )
    crop_config = _make_crop_config()

    head = ClassifierHead()
    result = head.predict(payload, image=None, crop_config=crop_config)

    assert result.used_stub is True
    assert result.labels[0].name == "leaf_spot"
    assert result.top1_confidence == pytest.approx(0.61)
