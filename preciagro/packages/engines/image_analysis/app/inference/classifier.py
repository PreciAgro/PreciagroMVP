"""Classifier head built on top of timm backbones with a heuristic fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import torch
    from timm import create_model
    from timm.data import create_transform, resolve_data_config
except ImportError:  # pragma: no cover - optional heavy deps
    torch = None
    create_model = None
    create_transform = None
    resolve_data_config = None

from PIL import Image

from preciagro.packages.engines.image_analysis import diagnose
from preciagro.packages.shared.schemas import DiagnosisOut

from ..core.registry import CropModelConfig
from ..models import ImageAnalysisRequest

LOGGER = logging.getLogger(__name__)


@dataclass
class PredictedLabel:
    """Container for a predicted label and confidence."""

    name: str
    confidence: float


@dataclass
class ClassifierResult:
    """Classifier inference result with optional fallback metadata."""

    labels: List[PredictedLabel]
    model_version: str
    used_stub: bool = False
    raw_topk: List[Tuple[int, float]] | None = None

    @property
    def top1_confidence(self) -> float:
        """Safe accessor for the top-1 confidence."""

        return self.labels[0].confidence if self.labels else 0.0

    @property
    def top1_label(self) -> Optional[str]:
        """Safe accessor for the top-1 label name."""

        return self.labels[0].name if self.labels else None


class ClassifierHead:
    """Wraps timm backbones and handles caching, transforms, and fallbacks."""

    def __init__(self) -> None:
        self._model_cache: Dict[str, dict] = {}
        self._device = self._resolve_device()

    def predict(
        self,
        payload: ImageAnalysisRequest,
        image: Optional[np.ndarray],
        crop_config: CropModelConfig,
    ) -> ClassifierResult:
        """Return the ordered list of predicted labels for an image."""

        if image is None or not self._timm_available():
            LOGGER.info("Classifier head running in heuristic mode (no image or timm unavailable)")
            return self._heuristic_labels(payload)

    def get_bundle(self, crop_config: CropModelConfig) -> dict:
        """Expose the cached model bundle for auxiliary tasks (e.g., Grad-CAM)."""

        return self._load_model(crop_config)

        try:
            bundle = self._load_model(crop_config)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to load classifier backbone; falling back to heuristic", exc_info=exc)
            return self._heuristic_labels(payload)

        try:
            logits = self._forward(bundle, image, crop_config)
            labels = self._to_labels(bundle, logits, crop_config.classifier.top_k)
            return ClassifierResult(
                labels=labels,
                model_version=bundle["model_version"],
                used_stub=False,
                raw_topk=[
                    (int(idx), float(prob)) for idx, prob in self._topk_indices(logits, crop_config.classifier.top_k)
                ],
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Classifier inference failed; using heuristic fallback", exc_info=exc)
            return self._heuristic_labels(payload)

    def _timm_available(self) -> bool:
        return torch is not None and create_model is not None and create_transform is not None

    def _resolve_device(self) -> str:
        if torch is None:
            return "cpu"
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():  # type: ignore[attr-defined]
            return "mps"
        return "cpu"

    def _heuristic_labels(self, payload: ImageAnalysisRequest) -> ClassifierResult:
        diagnosis: DiagnosisOut = diagnose(payload.image_base64 or "", payload.crop)
        labels = [PredictedLabel(name=item.name, confidence=item.score) for item in diagnosis.labels]
        return ClassifierResult(labels=labels, model_version=diagnosis.model_version, used_stub=True, raw_topk=None)

    def _load_model(self, crop_config: CropModelConfig) -> dict:
        """Load and cache the configured timm backbone."""

        classifier_cfg = crop_config.classifier
        cache_key = f"{classifier_cfg.name}|{classifier_cfg.weights_path}|{classifier_cfg.threshold}"

        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        if not self._timm_available():
            msg = "timm/torch not available in runtime"
            raise RuntimeError(msg)

        model = create_model(classifier_cfg.name, pretrained=True)
        model.eval()
        model.to(self._device)

        # Optionally load fine-tuned weights if present locally
        model_version = "pretrained"
        weights_path = classifier_cfg.weights_path
        if weights_path and weights_path.startswith(("az://", "s3://", "gs://")):
            LOGGER.info("Remote weight URI detected (%s); skipping local load in this environment", weights_path)
        elif weights_path:
            resolved = Path(weights_path)
            if resolved.exists():
                LOGGER.info("Loading fine-tuned weights from %s", resolved)
                state = torch.load(resolved, map_location=self._device)
                state_dict = state.get("state_dict") if isinstance(state, dict) and "state_dict" in state else state
                model.load_state_dict(state_dict, strict=False)
                model_version = resolved.name
            else:
                LOGGER.warning("Weights path %s not found; using pretrained weights", resolved)

        data_cfg = resolve_data_config({}, model=model)
        transform = create_transform(**data_cfg, is_training=False)
        class_names = self._extract_class_names(model)

        bundle = {
            "model": model,
            "transform": transform,
            "class_names": class_names,
            "model_version": f"{classifier_cfg.name}:{model_version}",
        }
        self._model_cache[cache_key] = bundle
        return bundle

    def _forward(self, bundle: dict, image: np.ndarray, crop_config: CropModelConfig):
        """Run the model forward pass with optional simple TTA."""

        if torch is None:
            msg = "Torch not available during forward pass"
            raise RuntimeError(msg)

        transform = bundle["transform"]
        model = bundle["model"]
        tensors: List[torch.Tensor] = []

        tensors.append(self._prepare_tensor(image, transform))

        if crop_config.classifier.tta:
            flipped = cv2.flip(image, 1)
            tensors.append(self._prepare_tensor(flipped, transform))

        batch = torch.stack(tensors).to(self._device)
        with torch.no_grad():
            logits = model(batch)

        logits = logits.mean(dim=0, keepdim=True)
        return logits.squeeze(0).cpu()

    def _prepare_tensor(self, image: np.ndarray, transform) -> "torch.Tensor":
        """Convert BGR numpy array into normalized tensor for model input."""

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        tensor = transform(pil_image)
        return tensor

    def _to_labels(self, bundle: dict, logits: "torch.Tensor", top_k: int) -> List[PredictedLabel]:
        """Convert logits into sorted label predictions."""

        if torch is None:
            return []

        probabilities = torch.softmax(logits, dim=-1)
        top_prob, top_idx = torch.topk(probabilities, k=min(top_k, probabilities.shape[-1]))

        class_names = bundle.get("class_names") or []
        labels: List[PredictedLabel] = []
        for prob, idx in zip(top_prob.tolist(), top_idx.tolist()):
            labels.append(PredictedLabel(name=self._class_name(class_names, idx), confidence=float(prob)))
        return labels

    def _topk_indices(self, logits: "torch.Tensor", top_k: int) -> List[Tuple[int, float]]:
        """Return top-k indices and probabilities for logging/metrics."""

        if torch is None:
            return []

        probabilities = torch.softmax(logits, dim=-1)
        top_prob, top_idx = torch.topk(probabilities, k=min(top_k, probabilities.shape[-1]))
        return list(zip(top_idx.tolist(), top_prob.tolist()))

    def _class_name(self, class_names: List[str], idx: int) -> str:
        if class_names and 0 <= idx < len(class_names):
            return class_names[idx]
        return f"class_{idx}"

    def _extract_class_names(self, model) -> List[str]:
        """Extract class names from timm model config when available."""

        candidates = []
        for attr in ("pretrained_cfg", "default_cfg", "config"):
            cfg = getattr(model, attr, None)
            if cfg and isinstance(cfg, dict) and "label_names" in cfg:
                candidates = cfg["label_names"]
                break
        return candidates or []
