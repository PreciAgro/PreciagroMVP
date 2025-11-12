"""Quality gate heuristics for incoming crop images."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import cv2
import numpy as np

from ..core.registry import QualityThresholdConfig


@dataclass
class QualityGateResult:
    """Outcome of the quality gate checks."""

    passed: bool = True
    notes: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


class QualityGate:
    """Computes a set of inexpensive heuristics to catch unusable images early."""

    def evaluate(
        self,
        image: Optional[np.ndarray],
        config: QualityThresholdConfig,
    ) -> QualityGateResult:
        """Run blur, exposure, and framing checks."""

        if image is None:
            return QualityGateResult(
                passed=False,
                notes=["Image could not be decoded. Please retake and ensure a clear capture."],
            )

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        metrics: Dict[str, float] = {}
        notes: List[str] = []

        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        metrics["blur"] = round(float(blur_score), 2)
        if blur_score < config.blur_threshold:
            notes.append(
                "Image appears blurry. Hold the device steady and focus on the target leaves."
            )

        exposure_score = float(gray.mean() / 255.0)
        metrics["exposure"] = round(exposure_score, 3)
        if exposure_score < config.exposure_min or exposure_score > config.exposure_max:
            notes.append(
                "Lighting is suboptimal. Capture in diffuse daylight and avoid deep shadows or glare."
            )

        height, width = gray.shape
        min_edge = min(height, width)
        metrics["min_edge"] = float(min_edge)
        if min_edge < config.min_resolution:
            notes.append(
                f"Image resolution ({min_edge}px) is below the recommended "
                f"{config.min_resolution}px minimum. Move closer or use a higher resolution setting."
            )

        h_start = int(height * 0.3)
        h_end = int(height * 0.7)
        w_start = int(width * 0.3)
        w_end = int(width * 0.7)
        center_focus = 1.0
        if h_end > h_start and w_end > w_start:
            center_roi = gray[h_start:h_end, w_start:w_end]
            global_mean = gray.mean() or 1.0
            center_focus = float(center_roi.mean() / global_mean)
        metrics["center_focus"] = round(center_focus, 3)
        if center_focus < config.center_focus_min:
            notes.append(
                "Subject not centered. Ensure the diseased leaf occupies most of the frame."
            )

        passed = not notes
        return QualityGateResult(passed=passed, notes=notes, metrics=metrics)
