"""Filesystem-based artifact storage."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from ..core import settings


class ArtifactStorage:
    """Simple helper that persists explainability artifacts to disk."""

    def __init__(self) -> None:
        self.base_path = Path(settings.ARTIFACT_STORAGE_DIR).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.base_url = settings.ARTIFACT_BASE_URL.rstrip("/")

    def store_heatmap(
        self,
        image_bgr: np.ndarray,
        crop: str,
        request_id: Optional[str],
        suffix: str = "gradcam",
    ) -> str:
        """Persist the heatmap image and return a relative/absolute URL."""

        return self._write_image(image_bgr, crop, request_id, suffix)

    def store_mask_overlay(
        self,
        overlay_bgr: np.ndarray,
        crop: str,
        request_id: Optional[str],
        suffix: str = "lesion-mask",
    ) -> str:
        """Persist lesion mask overlays using the same storage convention."""

        return self._write_image(overlay_bgr, crop, request_id, suffix)

    def store_mask_binary(
        self,
        mask: np.ndarray,
        crop: str,
        request_id: Optional[str],
        suffix: str = "lesion-mask-binary",
    ) -> str:
        """Persist the raw binary mask for downstream analytics."""

        binary = (mask.astype(np.uint8) * 255)
        return self._write_image(binary, crop, request_id, suffix)

    def _write_image(
        self,
        image_bgr: np.ndarray,
        crop: str,
        request_id: Optional[str],
        suffix: str,
    ) -> str:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        identifier = request_id or uuid.uuid4().hex[:8]
        safe_crop = crop or "generic"
        relative_path = Path(safe_crop) / f"{ts}_{identifier}_{suffix}.png"
        target = self.base_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(target), image_bgr)

        if self.base_url:
            return f"{self.base_url}/{relative_path.as_posix()}"
        return str(target)
