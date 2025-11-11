from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np

from .model_registry import model_manager


logger = logging.getLogger(__name__)


class YieldOutlook:
    """Provides yield estimation and outlook using pretrained regressors + fallback."""

    MODEL_BY_CROP = {
        "maize": "yield_estimator_maize",
    }

    def __init__(self):
        self._model_cache: Dict[str, object] = {}

    def p_bands(self, crop: Optional[str], season_features: dict) -> Tuple[float, float, float, str]:
        model_name = self.MODEL_BY_CROP.get((crop or "").lower())
        prediction = None
        model_version = "heuristic_v0"

        if model_name:
            model = self._load_model(model_name)
            vector = self._vectorize(model_name, season_features)
            if model is not None and vector is not None:
                try:
                    y = float(model.predict([vector])[0])
                    prediction = (y - 0.6, y, y + 0.6)
                    meta = model_manager.metadata(model_name) or {}
                    model_version = meta.get("version", model_version)
                except Exception:  # pragma: no cover - depends on artifact
                    logger.exception("Yield model inference failed; falling back")

        if prediction is None:
            prediction = self._heuristic(season_features)

        return prediction[0], prediction[1], prediction[2], model_version

    def _load_model(self, model_name: str):
        if model_name not in self._model_cache:
            self._model_cache[model_name] = model_manager.load_joblib(model_name)
        return self._model_cache[model_name]

    @staticmethod
    def _vectorize(model_name: str, features: dict) -> Optional[list[float]]:
        if model_name == "yield_estimator_maize":
            keys = [
                "ndvi_max_vegetative",
                "ndvi_avg_reproductive",
                "cumulative_rain_mm",
                "whc_mm",
                "gdd_total",
                "planting_date_doy",
            ]
            return [float(features.get(key, 0.0)) for key in keys]
        return None

    @staticmethod
    def _heuristic(features: dict) -> Tuple[float, float, float]:
        cum_rain = float(features.get("cumulative_rain_mm") or features.get("cum_rain", 0.0))
        p50 = cum_rain * 0.005 + 2.0
        return max(0.3, p50 - 0.7), p50, p50 + 0.7


yo = YieldOutlook()
