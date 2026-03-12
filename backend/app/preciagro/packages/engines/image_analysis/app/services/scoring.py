"""Utilities for aggregating health scores."""

from __future__ import annotations


def compute_health_score(
    disease_confidence: float,
    lesion_pct: float | None,
    quality_passed: bool,
) -> float:
    """Combine classifier confidence, lesion coverage, and quality gate result."""

    score = max(0.0, min(1.0, disease_confidence))

    if lesion_pct is not None:
        lesion_pct = max(0.0, min(1.0, lesion_pct))
        score *= 1 - lesion_pct

    if not quality_passed:
        score *= 0.85

    return round(score, 2)
