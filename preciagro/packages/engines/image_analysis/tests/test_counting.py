from __future__ import annotations

import numpy as np

from preciagro.packages.engines.image_analysis.app.core.registry import (
    ClassifierConfig,
    CountingConfig,
    CropModelConfig,
)
from preciagro.packages.engines.image_analysis.app.counting import CountingEngine


def _crop_config() -> CropModelConfig:
    return CropModelConfig(
        classifier=ClassifierConfig(name="efficientnet_v2_s", weights_path=""),
        counting=CountingConfig(enabled=True, classes=["fruit", "pest"]),
    )


def test_counting_stub_runs_without_yolo() -> None:
    """Counting engine should gracefully fall back when ultralytics is unavailable."""

    engine = CountingEngine()
    result = engine.count(image_bgr=np.zeros((10, 10, 3), dtype=np.uint8), crop_config=_crop_config())

    assert result.used_stub is True
    assert result.counts == {"fruit": 0, "pest": 0}
