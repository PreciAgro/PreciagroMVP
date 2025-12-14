from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from ..models.schemas import TelemetryBatch
from .model_registry import model_manager


logger = logging.getLogger(__name__)


@dataclass
class StagePrediction:
    stage: Optional[str]
    confidence: float


class GrowthStageEstimator:
    """Wraps pretrained stage classifier with heuristic fallback."""

    MODEL_NAME = "crop_stage_detector"

    def __init__(self):
        self._model = None

    def predict(self, telemetry: TelemetryBatch, crop: Optional[str] = None) -> StagePrediction:
        features = self._build_features(telemetry, crop)
        model = self._load_model()
        if model is not None and features is not None:
            try:
                probs = model.predict_proba([features])[0]
                classes = getattr(model, "classes_", None)
                if classes is not None:
                    idx = int(np.argmax(probs))
                    return StagePrediction(stage=str(classes[idx]), confidence=float(probs[idx]))
            except Exception:  # pragma: no cover - depends on external artifact
                logger.exception("Stage model inference failed; falling back")
        return self._heuristic_stage(telemetry)

    def _load_model(self):
        if self._model is None:
            self._model = model_manager.load_joblib(self.MODEL_NAME)
        return self._model

    @staticmethod
    def _build_features(telemetry: TelemetryBatch, crop: Optional[str]) -> Optional[list[float]]:
        if not telemetry.vi:
            return None
        ndvi_vals = [point.ndvi or 0.0 for point in telemetry.vi[-14:]]
        ndvi_avg = float(np.mean(ndvi_vals)) if ndvi_vals else 0.0
        ndvi_std = float(np.std(ndvi_vals)) if ndvi_vals else 0.0
        days_since = len(telemetry.vi)
        return [ndvi_avg, ndvi_std, days_since]

    @staticmethod
    def _heuristic_stage(tb: TelemetryBatch) -> StagePrediction:
        if not tb.vi:
            return StagePrediction(stage=None, confidence=0.0)
        ndvi = tb.vi[-1].ndvi or 0.0
        if ndvi < 0.2:
            return StagePrediction("emergence", 0.45)
        if ndvi < 0.5:
            return StagePrediction("vegetative", 0.55)
        if ndvi < 0.75:
            return StagePrediction("reproductive", 0.55)
        return StagePrediction("maturity", 0.5)


growth_stage_estimator = GrowthStageEstimator()
