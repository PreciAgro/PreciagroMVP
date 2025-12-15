"""WeightingService - Computes weighted feedback artifacts.

Implements the weighting formula:
Weight = base_confidence × farmer_experience_factor × historical_accuracy_factor
         × model_confidence_factor × environmental_stability_factor

This formula is the core of FLE's signal quality assessment.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..models.feedback_event import FeedbackEvent
from ..models.weighted_feedback import WeightedFeedback
from ..contracts.upstream import (
    FarmerProfileContext,
    RecommendationContext,
    OutcomeTimingContext,
)
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class WeightFactors:
    """Individual weight factors for transparency."""

    base_confidence: float
    farmer_experience_factor: float
    historical_accuracy_factor: float
    model_confidence_factor: float
    environmental_stability_factor: float

    @property
    def final_weight(self) -> float:
        """Calculate final weight using the formula."""
        return (
            self.base_confidence
            * self.farmer_experience_factor
            * self.historical_accuracy_factor
            * self.model_confidence_factor
            * self.environmental_stability_factor
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "base_confidence": self.base_confidence,
            "farmer_experience_factor": self.farmer_experience_factor,
            "historical_accuracy_factor": self.historical_accuracy_factor,
            "model_confidence_factor": self.model_confidence_factor,
            "environmental_stability_factor": self.environmental_stability_factor,
            "final_weight": self.final_weight,
        }


class WeightingService:
    """Service for computing weighted feedback.

    The weighting formula:
    Weight = base_confidence × farmer_experience_factor
             × historical_accuracy_factor × model_confidence_factor
             × environmental_stability_factor

    Each factor is between 0 and 1, so final weight is also 0-1.
    """

    def __init__(self):
        """Initialize weighting service."""
        self._weighted_store: Dict[str, WeightedFeedback] = {}

    async def compute_weight(
        self,
        event: FeedbackEvent,
        farmer_profile: Optional[FarmerProfileContext] = None,
        recommendation_context: Optional[RecommendationContext] = None,
        timing_context: Optional[OutcomeTimingContext] = None,
        validation_flags: Optional[Dict[str, bool]] = None,
    ) -> WeightedFeedback:
        """Compute weighted feedback from a feedback event.

        Args:
            event: FeedbackEvent to weight
            farmer_profile: Farmer profile context from upstream
            recommendation_context: Recommendation context from upstream
            timing_context: Timing context from upstream
            validation_flags: Validation flags from validation service

        Returns:
            WeightedFeedback artifact
        """
        validation_flags = validation_flags or {}

        # Compute individual factors
        factors = self._compute_factors(
            event=event,
            farmer_profile=farmer_profile,
            recommendation_context=recommendation_context,
            timing_context=timing_context,
        )

        # Compute trust score (combination of factors)
        trust_score = self._compute_trust_score(factors, event)

        # Compute quality score (based on feedback completeness)
        quality_score = self._compute_quality_score(event)

        # Determine flags
        is_flagged = self._should_flag(factors, validation_flags)
        flag_reasons = self._get_flag_reasons(factors, validation_flags)

        # Create weighted feedback artifact
        weighted = WeightedFeedback(
            source_feedback_id=event.feedback_id,
            recommendation_id=event.recommendation_id,
            final_weight=factors.final_weight,
            base_confidence=factors.base_confidence,
            farmer_experience_factor=factors.farmer_experience_factor,
            historical_accuracy_factor=factors.historical_accuracy_factor,
            model_confidence_factor=factors.model_confidence_factor,
            environmental_stability_factor=factors.environmental_stability_factor,
            trust_score=trust_score,
            quality_score=quality_score,
            is_flagged=is_flagged,
            flag_reasons=flag_reasons,
            is_noise=validation_flags.get("is_noise", False),
            is_duplicate=validation_flags.get("is_duplicate", False),
            is_contradiction=validation_flags.get("is_contradiction", False),
            duplicate_of_id=validation_flags.get("duplicate_of_id"),
            contradiction_with_ids=validation_flags.get("contradiction_ids", []),
            region_code=event.region_code,
        )

        # Store
        self._weighted_store[weighted.weighted_id] = weighted

        logger.info(
            f"Computed weight for feedback {event.feedback_id}: "
            f"weight={factors.final_weight:.3f}, trust={trust_score:.3f}",
            extra={
                "feedback_id": event.feedback_id,
                "weighted_id": weighted.weighted_id,
                "factors": factors.to_dict(),
            },
        )

        return weighted

    def _compute_factors(
        self,
        event: FeedbackEvent,
        farmer_profile: Optional[FarmerProfileContext],
        recommendation_context: Optional[RecommendationContext],
        timing_context: Optional[OutcomeTimingContext],
    ) -> WeightFactors:
        """Compute individual weight factors.

        Args:
            event: FeedbackEvent
            farmer_profile: Farmer profile context
            recommendation_context: Recommendation context
            timing_context: Timing context

        Returns:
            WeightFactors with all components
        """
        # Base confidence
        base_confidence = self._compute_base_confidence(event)

        # Farmer experience factor
        farmer_experience = self._compute_farmer_experience_factor(farmer_profile)

        # Historical accuracy factor
        historical_accuracy = self._compute_historical_accuracy_factor(farmer_profile)

        # Model confidence factor
        model_confidence = self._compute_model_confidence_factor(recommendation_context)

        # Environmental stability factor
        environmental_stability = self._compute_environmental_stability_factor(timing_context)

        return WeightFactors(
            base_confidence=base_confidence,
            farmer_experience_factor=farmer_experience,
            historical_accuracy_factor=historical_accuracy,
            model_confidence_factor=model_confidence,
            environmental_stability_factor=environmental_stability,
        )

    def _compute_base_confidence(self, event: FeedbackEvent) -> float:
        """Compute base confidence from feedback type and content.

        Args:
            event: FeedbackEvent

        Returns:
            Base confidence score (0-1)
        """
        base = settings.BASE_CONFIDENCE  # 0.5 default

        # Explicit feedback with rating is more reliable
        if event.feedback_type == "explicit":
            if event.rating:
                base += 0.2
            if event.comment:
                # Comments indicate more engagement
                base += 0.1

        # Outcome feedback with evidence is most reliable
        elif event.feedback_type == "outcome":
            if event.action_executed:
                base += 0.3
            if event.raw_payload.get("evidence_photo_refs"):
                base += 0.1

        # Implicit feedback is less reliable
        elif event.feedback_type == "implicit":
            if event.clicked_action:
                base += 0.1
            if event.view_duration_seconds and event.view_duration_seconds > 30:
                base += 0.05

        return min(base, 1.0)

    def _compute_farmer_experience_factor(
        self,
        farmer_profile: Optional[FarmerProfileContext],
    ) -> float:
        """Compute farmer experience factor.

        Args:
            farmer_profile: Farmer profile context

        Returns:
            Experience factor (0-1)
        """
        if not farmer_profile:
            return settings.NOVICE_EXPERIENCE_FACTOR  # Default to novice

        level = farmer_profile.experience_level

        if level == "expert":
            factor = settings.EXPERT_EXPERIENCE_FACTOR
        elif level == "intermediate":
            factor = settings.INTERMEDIATE_EXPERIENCE_FACTOR
        else:
            factor = settings.NOVICE_EXPERIENCE_FACTOR

        # Boost for verified identity
        if farmer_profile.verified_identity:
            factor = min(factor + 0.1, 1.0)

        # Boost for trusted contributor
        if farmer_profile.trusted_contributor:
            factor = min(factor + 0.15, 1.0)

        return factor

    def _compute_historical_accuracy_factor(
        self,
        farmer_profile: Optional[FarmerProfileContext],
    ) -> float:
        """Compute historical accuracy factor.

        Args:
            farmer_profile: Farmer profile context

        Returns:
            Accuracy factor (0-1)
        """
        if not farmer_profile:
            return 0.5  # Unknown accuracy

        if farmer_profile.historical_accuracy is not None:
            # Direct accuracy score
            return farmer_profile.historical_accuracy

        # Compute from counts if available
        if farmer_profile.total_feedback_count > 0:
            accuracy = farmer_profile.accurate_feedback_count / farmer_profile.total_feedback_count
            return accuracy

        return 0.5  # Unknown

    def _compute_model_confidence_factor(
        self,
        recommendation_context: Optional[RecommendationContext],
    ) -> float:
        """Compute model confidence factor.

        Higher model confidence means we trust the model's prediction,
        so feedback that contradicts it may be weighted differently.

        Args:
            recommendation_context: Recommendation context

        Returns:
            Model confidence factor (0-1)
        """
        if not recommendation_context:
            return 0.5  # Unknown model confidence

        model_conf = recommendation_context.confidence

        # Transform: higher model confidence = we're more confident
        # in our assessment, so feedback weight is slightly higher
        return 0.5 + (model_conf * 0.5)

    def _compute_environmental_stability_factor(
        self,
        timing_context: Optional[OutcomeTimingContext],
    ) -> float:
        """Compute environmental stability factor.

        Stable conditions make feedback more reliable.

        Args:
            timing_context: Timing context

        Returns:
            Stability factor (0-1)
        """
        if not timing_context:
            return 0.7  # Unknown stability

        # Weather stability
        weather = timing_context.weather_stability or 0.7

        # Season alignment
        season = timing_context.season_alignment or 0.7

        # Combine
        stability = (weather * 0.6) + (season * 0.4)

        # Time variance penalty
        if timing_context.timing_variance_factor:
            if timing_context.timing_variance_factor > 0.5:
                stability *= 0.8  # Reduce for high variance

        return min(max(stability, 0.0), 1.0)

    def _compute_trust_score(
        self,
        factors: WeightFactors,
        event: FeedbackEvent,
    ) -> float:
        """Compute overall trust score.

        Args:
            factors: Weight factors
            event: FeedbackEvent

        Returns:
            Trust score (0-1)
        """
        # Trust is weighted average of factors
        trust = (
            factors.farmer_experience_factor * 0.3
            + factors.historical_accuracy_factor * 0.4
            + factors.base_confidence * 0.2
            + factors.environmental_stability_factor * 0.1
        )

        return trust

    def _compute_quality_score(self, event: FeedbackEvent) -> float:
        """Compute quality score based on completeness.

        Args:
            event: FeedbackEvent

        Returns:
            Quality score (0-1)
        """
        score = 0.5  # Base

        if event.feedback_type == "explicit":
            if event.rating:
                score += 0.2
            if event.comment:
                score += 0.2
            if event.feedback_category:
                score += 0.1

        elif event.feedback_type == "outcome":
            if event.outcome_category:
                score += 0.3
            if event.action_executed is not None:
                score += 0.2

        elif event.feedback_type == "implicit":
            if event.view_duration_seconds:
                score += 0.2
            if event.clicked_action is not None:
                score += 0.2

        return min(score, 1.0)

    def _should_flag(
        self,
        factors: WeightFactors,
        validation_flags: Dict[str, bool],
    ) -> bool:
        """Determine if feedback should be flagged for review.

        Args:
            factors: Weight factors
            validation_flags: Validation results

        Returns:
            True if should be flagged
        """
        # Flag if weight is too low
        if factors.final_weight < settings.FLAG_THRESHOLD_WEIGHT:
            return True

        # Flag if contradiction
        if validation_flags.get("is_contradiction"):
            return True

        # Flag if noise
        if validation_flags.get("is_noise"):
            return True

        return False

    def _get_flag_reasons(
        self,
        factors: WeightFactors,
        validation_flags: Dict[str, bool],
    ) -> list[str]:
        """Get list of flag reasons.

        Args:
            factors: Weight factors
            validation_flags: Validation results

        Returns:
            List of flag reason strings
        """
        reasons = []

        if factors.final_weight < settings.FLAG_THRESHOLD_WEIGHT:
            reasons.append(f"low_weight:{factors.final_weight:.3f}")

        if validation_flags.get("is_contradiction"):
            reasons.append("contradiction")

        if validation_flags.get("is_noise"):
            reasons.append(f"noise:{validation_flags.get('noise_reason', 'unknown')}")

        if validation_flags.get("is_duplicate"):
            reasons.append("duplicate")

        return reasons

    async def get_weighted(self, weighted_id: str) -> Optional[WeightedFeedback]:
        """Get weighted feedback by ID.

        Args:
            weighted_id: Weighted feedback ID

        Returns:
            WeightedFeedback if found
        """
        return self._weighted_store.get(weighted_id)

    async def get_weighted_for_recommendation(
        self,
        recommendation_id: str,
    ) -> list[WeightedFeedback]:
        """Get all weighted feedback for a recommendation.

        Args:
            recommendation_id: Recommendation ID

        Returns:
            List of WeightedFeedback
        """
        return [
            w for w in self._weighted_store.values() if w.recommendation_id == recommendation_id
        ]
