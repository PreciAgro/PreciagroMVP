"""SAM2 integration (with saliency fallback) for lesion quantification."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from ..core.registry import CropModelConfig
from ..storage.checkpoints import CheckpointManager

try:  # pragma: no cover - optional heavy dependency
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
except ImportError:  # pragma: no cover
    build_sam2 = None
    SAM2ImagePredictor = None

try:  # pragma: no cover
    import torch
except ImportError:  # pragma: no cover
    torch = None

LOGGER = logging.getLogger(__name__)


@dataclass
class LesionSegmentation:
    """In-memory representation of the lesion mask."""

    mask: np.ndarray
    overlay_bgr: np.ndarray
    area_ratio: float


class LesionSegmenter:
    """Runs SAM2 (when available) or a saliency fallback to estimate lesion coverage."""

    def __init__(self) -> None:
        self._predictor_cache: dict[str, SAM2ImagePredictor] = {}
        self.device = self._resolve_device()
        self.checkpoints = CheckpointManager()

    @property
    def available(self) -> bool:
        return build_sam2 is not None and SAM2ImagePredictor is not None and torch is not None

    def segment(
        self,
        image_bgr: np.ndarray,
        crop_config: CropModelConfig,
        heatmap: Optional[np.ndarray],
    ) -> Optional[LesionSegmentation]:
        """Return lesion mask + overlay when segmentation is enabled."""

        if image_bgr is None:
            return None

        mask: Optional[np.ndarray] = None
        if self.available:
            try:
                predictor = self._load_predictor(crop_config)
                mask = self._predict_with_sam(predictor, image_bgr, heatmap)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("SAM2 inference failed, falling back to saliency mask: %s", exc)
                mask = None

        if mask is None:
            mask = self._saliency_mask(image_bgr, heatmap)

        if mask is None:
            return None

        overlay = self._mask_to_overlay(image_bgr, mask)
        area_ratio = float(mask.sum() / mask.size)
        return LesionSegmentation(mask=mask, overlay_bgr=overlay, area_ratio=area_ratio)

    def _load_predictor(self, crop_config: CropModelConfig):
        seg_cfg = crop_config.segmentation
        cache_key = seg_cfg.weights_path or seg_cfg.model or "default"
        if cache_key in self._predictor_cache:
            return self._predictor_cache[cache_key]

        if not self.available:
            raise RuntimeError("SAM2 libraries not available in runtime")

        model_name = seg_cfg.model or "sam2_hiera_small"
        weights_path = self.checkpoints.resolve(seg_cfg.weights_path, seg_cfg.weights_uri)
        sam = build_sam2(model_name=model_name, checkpoint=str(weights_path), device=self.device)
        predictor = SAM2ImagePredictor(sam)
        self._predictor_cache[cache_key] = predictor
        return predictor

    def _predict_with_sam(
        self,
        predictor,
        image_bgr: np.ndarray,
        heatmap: Optional[np.ndarray],
    ) -> Optional[np.ndarray]:
        """Run SAM2 for a single seeded point."""

        if torch is None:
            return None

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        predictor.set_image(rgb)

        h, w = rgb.shape[:2]
        point = self._select_seed_point(heatmap, width=w, height=h)
        point_coords = np.array([[point[0], point[1]]], dtype=np.float32)
        point_labels = np.array([1], dtype=np.int32)

        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True,
        )
        if masks is None or len(masks) == 0:
            return None
        mask = masks[np.argmax(scores)]
        return mask.astype(bool)

    def _saliency_mask(
        self,
        image_bgr: np.ndarray,
        heatmap: Optional[np.ndarray],
    ) -> Optional[np.ndarray]:
        """Fallback mask built from Grad-CAM heatmap or HSV heuristics."""

        mask_bool: Optional[np.ndarray] = None

        if heatmap is not None:
            cam = heatmap.astype(np.float32)
            cam = cv2.resize(cam, (image_bgr.shape[1], image_bgr.shape[0]))
            cam /= cam.max() + 1e-6
            for quantile in (0.9, 0.95, 0.97, 0.99):
                candidate = cam >= np.quantile(cam, quantile)
                ratio = candidate.mean()
                if 0 < ratio < 0.9:
                    mask_bool = candidate
                    break
            if mask_bool is None:
                mask_bool = cam >= np.quantile(cam, 0.995)
        else:
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            value_channel = hsv[:, :, 2].astype(np.float32) / 255.0
            inverted = 1.0 - value_channel
            for quantile in (0.85, 0.9, 0.95):
                thresh = np.quantile(inverted, quantile)
                mask = inverted >= thresh
                mask_uint = mask.astype(np.uint8) * 255
                mask_uint = cv2.medianBlur(mask_uint, 5)
                candidate = mask_uint > 0
                ratio = candidate.mean()
                if 0 < ratio < 0.9:
                    mask_bool = candidate
                    break
            if mask_bool is None:
                mask_bool = inverted >= np.quantile(inverted, 0.99)

        if mask_bool is None or mask_bool.sum() == 0:
            return None
        return mask_bool

    def _mask_to_overlay(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Blend a red mask over the original image."""

        mask_uint = mask.astype(np.uint8) * 255
        color = np.zeros_like(image_bgr)
        color[:, :] = (0, 0, 255)
        overlay = image_bgr.copy()
        overlay = np.where(
            mask_uint[..., None] > 0, cv2.addWeighted(image_bgr, 0.4, color, 0.6, 0), image_bgr
        )
        return overlay

    def _select_seed_point(
        self,
        heatmap: Optional[np.ndarray],
        *,
        width: int,
        height: int,
    ) -> tuple[int, int]:
        """Pick the seed coordinate for SAM2."""

        if heatmap is not None and heatmap.size > 0:
            y, x = np.unravel_index(int(np.argmax(heatmap)), heatmap.shape)
            scale_x = max(x * width // heatmap.shape[1], 0)
            scale_y = max(y * height // heatmap.shape[0], 0)
            return (int(scale_x), int(scale_y))

        return (width // 2, height // 2)

    def _resolve_device(self) -> str:
        if torch is None:
            return "cpu"
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
