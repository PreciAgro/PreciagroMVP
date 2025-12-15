"""CLIP similarity fallback for low-confidence classifier predictions."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

try:  # pragma: no cover - optional heavy dependency
    import open_clip
except ImportError:  # pragma: no cover
    open_clip = None

try:  # pragma: no cover
    import torch
except ImportError:  # pragma: no cover
    torch = None

from ..core.registry import CropModelConfig, LabelRegistry, PromptSet, get_prompt_set
from .classifier import PredictedLabel

LOGGER = logging.getLogger(__name__)


class ClipFallback:
    """Computes CLIP similarities against curated prompts when requested."""

    def __init__(self, label_registry: LabelRegistry) -> None:
        self.label_registry = label_registry
        self._model_cache: dict[str, dict] = {}
        self._device = self._resolve_device()

    @property
    def available(self) -> bool:
        return open_clip is not None and torch is not None

    def rank(
        self,
        image: Optional[np.ndarray],
        crop: str,
        crop_config: CropModelConfig,
    ) -> Optional[PredictedLabel]:
        """Return the highest ranking CLIP prompt for this crop image."""

        if not image or image is None or not self.available or not crop_config.clip.enabled:
            return None

        candidates = self._build_candidates(get_prompt_set(crop))
        if not candidates:
            LOGGER.debug("No CLIP prompts configured for crop=%s", crop)
            return None

        try:
            bundle = self._load_clip_model(crop_config)
        except RuntimeError as exc:
            LOGGER.debug("CLIP fallback unavailable: %s", exc)
            return None

        image_tensor = self._encode_image(bundle["preprocess"], image)
        if image_tensor is None:
            return None

        texts = [text for _, text in candidates]
        label_names = [label for label, _ in candidates]
        try:
            scores = self._compute_similarity(bundle, image_tensor, texts)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("CLIP similarity failed: %s", exc)
            return None

        best_idx = int(scores.argmax().item())
        confidence = float(scores[best_idx].item())
        label_name = label_names[best_idx]
        return PredictedLabel(name=label_name, confidence=confidence)

    def _resolve_device(self) -> str:
        if torch is None:
            return "cpu"
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _build_candidates(self, prompt_set: PromptSet) -> List[Tuple[str, str]]:
        """Return (label, text) tuples for all configured prompts."""

        candidates: List[Tuple[str, str]] = []
        for prompt in (
            prompt_set.disease_prompts + prompt_set.nutrient_prompts + prompt_set.general_prompts
        ):
            label = self._infer_label(prompt)
            candidates.append((label, prompt))
        return candidates

    def _infer_label(self, prompt: str) -> str:
        """Map prompt text to a known alias when possible."""

        prompt_lower = prompt.lower()
        for alias in self.label_registry.alias_map.keys():
            if alias in prompt_lower:
                return alias
        return prompt

    def _load_clip_model(self, crop_config: CropModelConfig) -> dict:
        """Load CLIP model artifacts and cache them per config."""

        clip_cfg = crop_config.clip
        cache_key = f"{clip_cfg.model_name}|{clip_cfg.pretrained}"

        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        if open_clip is None or torch is None:
            msg = "open_clip or torch not installed in runtime"
            raise RuntimeError(msg)

        model, preprocess, _ = open_clip.create_model_and_transforms(
            clip_cfg.model_name, pretrained=clip_cfg.pretrained
        )
        tokenizer = open_clip.get_tokenizer(clip_cfg.model_name)
        model.eval()
        model.to(self._device)

        bundle = {
            "model": model,
            "preprocess": preprocess,
            "tokenizer": tokenizer,
        }
        self._model_cache[cache_key] = bundle
        return bundle

    def _encode_image(self, preprocess, image: np.ndarray):
        """Convert the incoming BGR frame into the tensor expected by CLIP."""

        if torch is None:
            return None

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        tensor = preprocess(pil_image).unsqueeze(0).to(self._device)
        return tensor

    def _compute_similarity(self, bundle: dict, image_tensor, texts: List[str]):
        """Compute normalized CLIP similarity scores."""

        if torch is None:
            raise RuntimeError("torch unavailable for CLIP similarity")

        model = bundle["model"]
        tokenizer = bundle["tokenizer"]

        with torch.no_grad():
            image_features = model.encode_image(image_tensor)
            image_features /= image_features.norm(dim=-1, keepdim=True)

            text_tokens = tokenizer(texts).to(self._device)
            text_features = model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)

            logits = (image_features @ text_features.T).squeeze(0)
            return torch.softmax(logits, dim=-1)
