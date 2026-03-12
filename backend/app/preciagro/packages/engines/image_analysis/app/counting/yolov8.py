"""Counting engine backed by YOLOv8 with graceful fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import cv2
import numpy as np

from ..core.registry import CountingConfig, CropModelConfig
from ..storage.checkpoints import CheckpointManager

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional heavy dependency
    from ultralytics import YOLO
except ImportError:  # pragma: no cover
    YOLO = None


@dataclass
class CountingResult:
    """Structured counting response for downstream serialization."""

    counts: Dict[str, int]
    model_version: str
    used_stub: bool = False


class CountingEngine:
    """Loads YOLO models per crop and produces object counts when enabled."""

    def __init__(self) -> None:
        self._model_cache: Dict[str, YOLO] = {}
        self._checkpoint_manager = CheckpointManager()

    @property
    def available(self) -> bool:
        return YOLO is not None

    def count(
        self,
        image_bgr: Optional[np.ndarray],
        crop_config: CropModelConfig,
    ) -> CountingResult:
        """Return counts for configured classes."""

        counting_cfg = crop_config.counting
        if not counting_cfg.enabled or image_bgr is None or not counting_cfg.classes:
            return CountingResult(counts={}, model_version="disabled", used_stub=True)

        if not self.available:
            LOGGER.info("Ultralytics YOLO not installed; returning heuristic counts")
            return self._stub_counts(counting_cfg)

        try:
            model = self._load_model(counting_cfg)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to load YOLO model, falling back to stub: %s", exc)
            return self._stub_counts(counting_cfg)

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        try:
            results = model.predict(rgb, verbose=False)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("YOLO prediction failed: %s", exc)
            return self._stub_counts(counting_cfg)

        counts: Dict[str, int] = {target: 0 for target in counting_cfg.classes}
        if not results:
            return CountingResult(counts=counts, model_version=str(model.ckpt_path))

        first = results[0]
        if not hasattr(first, "boxes") or first.boxes is None:
            return CountingResult(counts=counts, model_version=str(model.ckpt_path))

        names_map = getattr(model, "names", {}) or {}
        for box in first.boxes:
            cls_idx = int(box.cls[0]) if hasattr(box, "cls") else None
            if cls_idx is None:
                continue
            label = names_map.get(cls_idx, str(cls_idx))
            if label in counts:
                counts[label] += 1

        return CountingResult(counts=counts, model_version=str(model.ckpt_path))

    def _load_model(self, cfg: CountingConfig):
        cache_key = cfg.weights_path or cfg.model or "yolov8n"
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        if not self.available:
            raise RuntimeError("YOLO dependency missing")

        weights_path = self._checkpoint_manager.resolve(cfg.weights_path, cfg.weights_uri)
        LOGGER.info("Loading YOLO model from %s", weights_path)
        model = YOLO(str(weights_path))
        self._model_cache[cache_key] = model
        return model

    def _stub_counts(self, cfg: CountingConfig) -> CountingResult:
        """Simple heuristic stub for tests/non-ML environments."""

        counts = {label: 0 for label in cfg.classes}
        return CountingResult(counts=counts, model_version="stub", used_stub=True)
