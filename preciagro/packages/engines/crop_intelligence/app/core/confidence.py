"""
Confidence and uncertainty tracking for CIE outputs.
Attaches explicit uncertainty (state_conf, model_conf, data_gaps) to every action.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum


class ConfidenceSource(str, Enum):
    """Source of confidence degradation."""

    STATE_DETECTION = "state_detection"
    MODEL_PREDICTION = "model_prediction"
    DATA_QUALITY = "data_quality"
    DATA_GAPS = "data_gaps"
    TEMPORAL_STALENESS = "temporal_staleness"
    EXTERNAL_INTEGRATION = "external_integration"


@dataclass
class DataGap:
    """Specific data gap affecting confidence."""

    category: str  # "weather", "photo", "soil", "vi", "action_log"
    severity: str  # "minor", "moderate", "critical"
    description: str
    impact_on_confidence: float  # 0.0-1.0 penalty
    last_available: Optional[datetime] = None
    expected_frequency: Optional[str] = None  # e.g., "daily", "weekly"


@dataclass
class ConfidenceBreakdown:
    """Detailed confidence breakdown for transparency."""

    overall: float  # 0.0-1.0
    state_conf: float  # Confidence in crop stage detection
    model_conf: float  # Confidence in model predictions (yield, risk)
    data_quality: float  # Confidence based on data completeness/freshness
    data_gaps: List[DataGap] = field(default_factory=list)
    sources: Dict[ConfidenceSource, float] = field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> Dict:
        """Serialize to dict for JSON responses."""
        return {
            "overall": round(self.overall, 2),
            "state_confidence": round(self.state_conf, 2),
            "model_confidence": round(self.model_conf, 2),
            "data_quality": round(self.data_quality, 2),
            "data_gaps": [
                {
                    "category": gap.category,
                    "severity": gap.severity,
                    "description": gap.description,
                    "impact": round(gap.impact_on_confidence, 2),
                }
                for gap in self.data_gaps
            ],
            "explanation": self.explanation,
        }


@dataclass
class ActionConfidence:
    """Confidence associated with a specific action recommendation."""

    action_id: str
    action_type: str  # "nitrogen", "water", "disease", "photo_prompt"
    confidence: ConfidenceBreakdown
    should_display: bool  # False if confidence too low
    # User-facing warning if confidence marginal
    display_warning: Optional[str] = None


def calculate_state_confidence(
    last_photo_date: Optional[date], current_date: date, vi_history_days: int, ndvi_quality: str
) -> Tuple[float, List[DataGap]]:
    """
    Calculate confidence in crop stage detection.

    Args:
        last_photo_date: Date of last photo observation
        current_date: Current date
        vi_history_days: Days of VI data available
        ndvi_quality: Quality flag for NDVI ("good", "fair", "poor", "missing")

    Returns:
        (confidence_score, data_gaps)
    """
    conf = 1.0
    gaps = []

    # Photo freshness
    if last_photo_date is None:
        conf *= 0.50  # Major penalty - no visual confirmation
        gaps.append(
            DataGap(
                category="photo",
                severity="critical",
                description="No field photos available for stage verification",
                impact_on_confidence=0.50,
                expected_frequency="14 days",
            )
        )
    else:
        days_since_photo = (current_date - last_photo_date).days
        if days_since_photo > 21:
            penalty = min(0.40, days_since_photo / 100.0)
            conf *= 1.0 - penalty
            gaps.append(
                DataGap(
                    category="photo",
                    severity="moderate",
                    description=f"Last photo {days_since_photo} days old - stage may have changed",
                    impact_on_confidence=penalty,
                    last_available=datetime.combine(last_photo_date, datetime.min.time()),
                    expected_frequency="14 days",
                )
            )

    # VI data availability
    if vi_history_days < 7:
        penalty = 0.25
        conf *= 1.0 - penalty
        gaps.append(
            DataGap(
                category="vi",
                severity="moderate",
                description=f"Only {vi_history_days} days of VI data - insufficient for trend",
                impact_on_confidence=penalty,
                expected_frequency="7 days",
            )
        )

    # NDVI quality
    if ndvi_quality == "poor":
        conf *= 0.85
        gaps.append(
            DataGap(
                category="vi",
                severity="minor",
                description="NDVI quality degraded (cloud cover or sensor issues)",
                impact_on_confidence=0.15,
            )
        )
    elif ndvi_quality == "missing":
        conf *= 0.70
        gaps.append(
            DataGap(
                category="vi",
                severity="moderate",
                description="Recent NDVI data missing",
                impact_on_confidence=0.30,
            )
        )

    return conf, gaps


def calculate_model_confidence(
    model_type: str,
    training_samples: Optional[int],
    validation_metric: Optional[float],
    regional_match: bool,
    crop_match: bool,
) -> Tuple[float, str]:
    """
    Calculate confidence in model predictions (yield, risk, timing).

    Args:
        model_type: "yield", "disease", "nitrogen_timing", "water"
        training_samples: Number of samples model was trained on
        validation_metric: Model validation score (e.g., R², accuracy)
        regional_match: Does model training data include this region?
        crop_match: Does model training data include this crop?

    Returns:
        (confidence_score, explanation)
    """
    conf = 1.0
    reasons = []

    # Base model quality
    if validation_metric is not None:
        if validation_metric < 0.6:
            conf *= 0.70
            reasons.append(f"model validation: {validation_metric:.2f}")
        elif validation_metric < 0.75:
            conf *= 0.85

    # Training sample size
    if training_samples is not None:
        if training_samples < 50:
            conf *= 0.75
            reasons.append(f"limited training data (n={training_samples})")
        elif training_samples < 200:
            conf *= 0.90

    # Regional applicability
    if not regional_match:
        conf *= 0.80
        reasons.append("model not trained on this region")

    # Crop applicability
    if not crop_match:
        conf *= 0.75
        reasons.append("model not trained on this crop")

    explanation = f"{model_type} model confidence"
    if reasons:
        explanation += f" (adjusted: {', '.join(reasons)})"

    return conf, explanation


def calculate_data_quality_confidence(
    weather_gaps_days: int,
    weather_last_update: Optional[datetime],
    soil_data_source: str,
    action_log_completeness: float,  # 0-1, estimated from user engagement
) -> Tuple[float, List[DataGap]]:
    """
    Calculate confidence based on input data completeness and freshness.

    Args:
        weather_gaps_days: Number of days with missing weather data in last 30d
        weather_last_update: Timestamp of last weather observation
        soil_data_source: "soilgrids", "lab", "farmer_estimate"
        action_log_completeness: 0-1 score of how well actions are logged

    Returns:
        (confidence_score, data_gaps)
    """
    conf = 1.0
    gaps = []

    # Weather data quality
    if weather_gaps_days > 7:
        penalty = min(0.40, weather_gaps_days / 30.0)
        conf *= 1.0 - penalty
        gaps.append(
            DataGap(
                category="weather",
                severity="moderate" if weather_gaps_days < 15 else "critical",
                description=f"{weather_gaps_days} days of weather data missing in last 30d",
                impact_on_confidence=penalty,
                expected_frequency="daily",
            )
        )

    # Weather freshness
    if weather_last_update:
        hours_stale = (datetime.now() - weather_last_update).total_seconds() / 3600.0
        if hours_stale > 48:
            penalty = min(0.30, hours_stale / 240.0)  # Max penalty at 10 days
            conf *= 1.0 - penalty
            gaps.append(
                DataGap(
                    category="weather",
                    severity="moderate",
                    description=f"Weather data {int(hours_stale)} hours stale",
                    impact_on_confidence=penalty,
                    last_available=weather_last_update,
                    expected_frequency="daily",
                )
            )

    # Soil data quality
    soil_confidence = {"lab": 1.0, "soilgrids": 0.85, "farmer_estimate": 0.60, "unknown": 0.50}
    soil_conf = soil_confidence.get(soil_data_source, 0.70)
    conf *= soil_conf
    if soil_conf < 0.85:
        gaps.append(
            DataGap(
                category="soil",
                severity="minor" if soil_conf > 0.7 else "moderate",
                description=f"Soil data from {soil_data_source} - uncertainty ±15-25%",
                impact_on_confidence=1.0 - soil_conf,
            )
        )

    # Action log completeness
    if action_log_completeness < 0.70:
        penalty = (1.0 - action_log_completeness) * 0.20  # Up to 20% penalty
        conf *= 1.0 - penalty
        gaps.append(
            DataGap(
                category="action_log",
                severity="minor",
                description="Incomplete action history - limits learning",
                impact_on_confidence=penalty,
                expected_frequency="per action",
            )
        )

    return conf, gaps


def build_confidence_breakdown(
    state_conf: float,
    state_gaps: List[DataGap],
    model_conf: float,
    model_explanation: str,
    data_quality: float,
    data_gaps: List[DataGap],
) -> ConfidenceBreakdown:
    """
    Combine component confidences into overall breakdown.

    Confidence formula: overall = state_conf^0.4 × model_conf^0.3 × data_quality^0.3
    (Geometric mean with weights)
    """
    overall = (state_conf**0.4) * (model_conf**0.3) * (data_quality**0.3)

    all_gaps = state_gaps + data_gaps

    # Build explanation
    explanation_parts = []
    if state_conf < 0.80:
        explanation_parts.append(f"stage detection: {state_conf:.2f}")
    if model_conf < 0.80:
        explanation_parts.append(f"model: {model_conf:.2f}")
    if data_quality < 0.80:
        explanation_parts.append(f"data quality: {data_quality:.2f}")

    if explanation_parts:
        explanation = "Confidence reduced by " + ", ".join(explanation_parts)
    else:
        explanation = "High confidence - all inputs reliable"

    return ConfidenceBreakdown(
        overall=overall,
        state_conf=state_conf,
        model_conf=model_conf,
        data_quality=data_quality,
        data_gaps=all_gaps,
        sources={
            ConfidenceSource.STATE_DETECTION: state_conf,
            ConfidenceSource.MODEL_PREDICTION: model_conf,
            ConfidenceSource.DATA_QUALITY: data_quality,
        },
        explanation=explanation,
    )


def assess_action_confidence(
    action_id: str,
    action_type: str,
    confidence_breakdown: ConfidenceBreakdown,
    min_display_threshold: float = 0.40,
) -> ActionConfidence:
    """
    Determine if action should be displayed based on confidence.

    Args:
        action_id: Unique action identifier
        action_type: Type of action
        confidence_breakdown: Full confidence breakdown
        min_display_threshold: Minimum confidence to show action (default 0.40)

    Returns:
        ActionConfidence with display decision
    """
    overall_conf = confidence_breakdown.overall
    should_display = overall_conf >= min_display_threshold

    # Display warnings for marginal confidence
    display_warning = None
    if overall_conf < 0.60 and should_display:
        critical_gaps = [g for g in confidence_breakdown.data_gaps if g.severity == "critical"]
        if critical_gaps:
            gap_desc = critical_gaps[0].description
            display_warning = f"⚠️ Low confidence: {gap_desc}"
        else:
            display_warning = "⚠️ Limited data - monitor closely"

    return ActionConfidence(
        action_id=action_id,
        action_type=action_type,
        confidence=confidence_breakdown,
        should_display=should_display,
        display_warning=display_warning,
    )


def confidence_decay_over_time(
    base_confidence: float,
    recommendation_date: date,
    current_date: date,
    decay_rate_per_week: float = 0.10,
) -> float:
    """
    Apply temporal decay to confidence as recommendation ages.

    Args:
        base_confidence: Original confidence at recommendation time
        recommendation_date: Date recommendation was made
        current_date: Current date
        decay_rate_per_week: Fractional confidence loss per week (default 10%)

    Returns:
        Decayed confidence score
    """
    days_old = (current_date - recommendation_date).days
    weeks_old = days_old / 7.0
    decay_factor = (1.0 - decay_rate_per_week) ** weeks_old
    return base_confidence * decay_factor


def aggregate_confidence_for_multi_action_card(
    action_confidences: List[ActionConfidence],
) -> ConfidenceBreakdown:
    """
    Aggregate confidence across multiple actions in a single card.

    Uses minimum confidence (conservative approach) for overall score.
    """
    if not action_confidences:
        return ConfidenceBreakdown(
            overall=0.0,
            state_conf=0.0,
            model_conf=0.0,
            data_quality=0.0,
            explanation="No actions to assess",
        )

    # Take minimum (most conservative)
    min_overall = min(ac.confidence.overall for ac in action_confidences)
    min_state = min(ac.confidence.state_conf for ac in action_confidences)
    min_model = min(ac.confidence.model_conf for ac in action_confidences)
    min_data = min(ac.confidence.data_quality for ac in action_confidences)

    # Collect all unique gaps
    all_gaps = []
    seen_gaps = set()
    for ac in action_confidences:
        for gap in ac.confidence.data_gaps:
            gap_key = (gap.category, gap.description)
            if gap_key not in seen_gaps:
                all_gaps.append(gap)
                seen_gaps.add(gap_key)

    return ConfidenceBreakdown(
        overall=min_overall,
        state_conf=min_state,
        model_conf=min_model,
        data_quality=min_data,
        data_gaps=all_gaps,
        explanation=f"Card confidence based on {len(action_confidences)} actions (minimum approach)",
    )
