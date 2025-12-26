from __future__ import annotations

import numpy as np

from preciagro.packages.engines.image_analysis.app.core.registry import (
    ClassifierConfig,
    CropModelConfig,
    SegmentationConfig,
)
from preciagro.packages.engines.image_analysis.app.segmentation import LesionSegmenter


def _crop_config() -> CropModelConfig:
    return CropModelConfig(
        classifier=ClassifierConfig(
            name="efficientnet_v2_s",
            weights_path="",
        ),
        segmentation=SegmentationConfig(enabled=True),
    )


def test_saliency_fallback_returns_mask_when_sam_unavailable() -> None:
    """Even without SAM2 installed, the saliency fallback should estimate lesion coverage."""

    image = np.zeros((32, 32, 3), dtype=np.uint8)
    image[8:24, 8:24] = [0, 0, 200]

    heatmap = np.zeros((32, 32), dtype=np.uint8)
    heatmap[10:22, 10:22] = 200

    segmenter = LesionSegmenter()
    result = segmenter.segment(image_bgr=image, crop_config=_crop_config(), heatmap=heatmap)

    assert result is not None
    assert 0 < result.area_ratio < 1
    assert result.overlay_bgr.shape == image.shape
