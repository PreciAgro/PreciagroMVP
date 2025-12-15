"""SignalService - Translates weighted feedback into learning signals.

This service:
- Translates WeightedFeedback into typed LearningSignal
- Applies signal type classification
- Handles aggregation of multiple feedback items
- Prepares signals for routing to downstream engines
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from ..models.weighted_feedback import WeightedFeedback
from ..models.learning_signal import LearningSignal
from ..contracts.downstream import SignalType
from ..contracts.upstream import RecommendationContext
from ..config import settings

logger = logging.getLogger(__name__)


class SignalService:
    """Service for generating learning signals from weighted feedback.

    Signals are:
    - Typed with strict enum types
    - Scoped by target engine and region
    - Versioned for orchestration compatibility
    - Never propagate cross-region by default
    - Consumable without interpretation
    """

    def __init__(self):
        """Initialize signal service."""
        self._signal_store: Dict[str, LearningSignal] = {}

    async def generate_signal(
        self,
        weighted_feedback: WeightedFeedback,
        recommendation_context: Optional[RecommendationContext] = None,
        target_engine: str = "all",
    ) -> LearningSignal:
        """Generate a learning signal from weighted feedback.

        Args:
            weighted_feedback: WeightedFeedback artifact
            recommendation_context: Optional recommendation context
            target_engine: Target engine for this signal

        Returns:
            LearningSignal ready for routing
        """
        # Determine signal type
        signal_type = self._classify_signal_type(weighted_feedback)

        # Calculate signal strength
        signal_strength = self._calculate_signal_strength(weighted_feedback)

        # Create signal
        signal = LearningSignal(
            signal_type=signal_type,
            signal_strength=signal_strength,
            source_feedback_ids=[weighted_feedback.source_feedback_id],
            source_weighted_ids=[weighted_feedback.weighted_id],
            recommendation_id=weighted_feedback.recommendation_id,
            target_engine=target_engine,
            region_scope=weighted_feedback.region_code,
            cross_region_propagation=settings.CROSS_REGION_PROPAGATION,
            model_id=recommendation_context.model_id if recommendation_context else None,
            model_version=recommendation_context.model_version if recommendation_context else None,
            model_type=None,  # Would come from recommendation context
            feedback_count=1,
            average_weight=weighted_feedback.final_weight,
            confidence_score=weighted_feedback.trust_score,
            feedback_window_start=datetime.utcnow() - timedelta(hours=1),
            feedback_window_end=datetime.utcnow(),
            correlation_id=str(uuid4()),
            context={
                "is_flagged": weighted_feedback.is_flagged,
                "flag_reasons": weighted_feedback.flag_reasons,
            },
        )

        # Store signal
        self._signal_store[signal.signal_id] = signal

        logger.info(
            f"Generated {signal_type.value} signal for recommendation "
            f"{weighted_feedback.recommendation_id}",
            extra={
                "signal_id": signal.signal_id,
                "signal_type": signal_type.value,
                "signal_strength": signal_strength,
            },
        )

        return signal

    async def generate_aggregated_signal(
        self,
        weighted_items: List[WeightedFeedback],
        recommendation_context: Optional[RecommendationContext] = None,
        target_engine: str = "all",
    ) -> LearningSignal:
        """Generate an aggregated signal from multiple weighted feedback items.

        Args:
            weighted_items: List of WeightedFeedback artifacts
            recommendation_context: Optional recommendation context
            target_engine: Target engine for this signal

        Returns:
            Aggregated LearningSignal
        """
        if not weighted_items:
            raise ValueError("Cannot generate signal from empty list")

        # All items should be for the same recommendation
        rec_id = weighted_items[0].recommendation_id
        for item in weighted_items:
            if item.recommendation_id != rec_id:
                raise ValueError("All weighted items must be for the same recommendation")

        # Classify based on aggregate
        signal_type = self._classify_aggregate_signal_type(weighted_items)

        # Calculate aggregate strength
        signal_strength = self._calculate_aggregate_strength(weighted_items)

        # Calculate averages
        avg_weight = sum(w.final_weight for w in weighted_items) / len(weighted_items)
        avg_trust = sum(w.trust_score for w in weighted_items) / len(weighted_items)

        # Find time window
        min_time = min(w.processed_at for w in weighted_items)
        max_time = max(w.processed_at for w in weighted_items)

        # Region scope (use first, they should all be same)
        region = weighted_items[0].region_code

        signal = LearningSignal(
            signal_type=signal_type,
            signal_strength=signal_strength,
            source_feedback_ids=[w.source_feedback_id for w in weighted_items],
            source_weighted_ids=[w.weighted_id for w in weighted_items],
            recommendation_id=rec_id,
            target_engine=target_engine,
            region_scope=region,
            cross_region_propagation=settings.CROSS_REGION_PROPAGATION,
            model_id=recommendation_context.model_id if recommendation_context else None,
            model_version=recommendation_context.model_version if recommendation_context else None,
            feedback_count=len(weighted_items),
            average_weight=avg_weight,
            confidence_score=avg_trust,
            feedback_window_start=min_time,
            feedback_window_end=max_time,
            correlation_id=str(uuid4()),
            context={
                "aggregated": True,
                "flagged_count": sum(1 for w in weighted_items if w.is_flagged),
            },
        )

        self._signal_store[signal.signal_id] = signal

        logger.info(
            f"Generated aggregated {signal_type.value} signal from {len(weighted_items)} items",
            extra={
                "signal_id": signal.signal_id,
                "recommendation_id": rec_id,
            },
        )

        return signal

    def _classify_signal_type(self, weighted: WeightedFeedback) -> SignalType:
        """Classify signal type from weighted feedback.

        Args:
            weighted: WeightedFeedback

        Returns:
            SignalType enum
        """
        # If flagged for contradiction, return contradiction
        if weighted.is_contradiction:
            return SignalType.CONTRADICTION

        # If classified as noise
        if weighted.is_noise:
            return SignalType.NOISE

        # If weight is too low, uncertain
        if weighted.final_weight < settings.MIN_FEEDBACK_WEIGHT:
            return SignalType.UNCERTAIN

        # Determine positive/negative based on quality and trust
        # We need to look at the original feedback to determine this
        # For now, use trust score as proxy
        if weighted.trust_score >= 0.6:
            # High trust - consider positive
            if weighted.quality_score >= 0.6:
                return SignalType.POSITIVE
            else:
                return SignalType.UNCERTAIN
        elif weighted.trust_score <= 0.3:
            return SignalType.NEGATIVE
        else:
            return SignalType.UNCERTAIN

    def _classify_aggregate_signal_type(
        self,
        weighted_items: List[WeightedFeedback],
    ) -> SignalType:
        """Classify signal type from multiple weighted items.

        Args:
            weighted_items: List of WeightedFeedback

        Returns:
            SignalType based on aggregate
        """
        if not weighted_items:
            return SignalType.UNCERTAIN

        # Count contradictions
        contradiction_count = sum(1 for w in weighted_items if w.is_contradiction)
        if contradiction_count > len(weighted_items) * 0.3:
            return SignalType.CONTRADICTION

        # Count noise
        noise_count = sum(1 for w in weighted_items if w.is_noise)
        if noise_count > len(weighted_items) * 0.5:
            return SignalType.NOISE

        # Calculate average trust
        avg_trust = sum(w.trust_score for w in weighted_items) / len(weighted_items)
        avg_quality = sum(w.quality_score for w in weighted_items) / len(weighted_items)

        if avg_trust >= 0.6 and avg_quality >= 0.5:
            return SignalType.POSITIVE
        elif avg_trust <= 0.3:
            return SignalType.NEGATIVE
        else:
            return SignalType.UNCERTAIN

    def _calculate_signal_strength(self, weighted: WeightedFeedback) -> float:
        """Calculate signal strength from weighted feedback.

        Args:
            weighted: WeightedFeedback

        Returns:
            Signal strength (0-1)
        """
        # Strength is combination of weight and trust
        strength = (weighted.final_weight * 0.6) + (weighted.trust_score * 0.4)

        # Penalize for flags
        if weighted.is_flagged:
            strength *= 0.8

        return min(max(strength, 0.0), 1.0)

    def _calculate_aggregate_strength(
        self,
        weighted_items: List[WeightedFeedback],
    ) -> float:
        """Calculate aggregate signal strength.

        Args:
            weighted_items: List of WeightedFeedback

        Returns:
            Aggregate strength (0-1)
        """
        if not weighted_items:
            return 0.0

        # Weight by individual strength
        strengths = [self._calculate_signal_strength(w) for w in weighted_items]
        avg_strength = sum(strengths) / len(strengths)

        # Boost for multiple sources (more confidence)
        count_boost = min(len(weighted_items) / 10, 0.2)  # Max 0.2 boost

        return min(avg_strength + count_boost, 1.0)

    async def get_signal(self, signal_id: str) -> Optional[LearningSignal]:
        """Get signal by ID.

        Args:
            signal_id: Signal ID

        Returns:
            LearningSignal if found
        """
        return self._signal_store.get(signal_id)

    async def get_signals_for_engine(
        self,
        engine: str,
        region: Optional[str] = None,
        limit: int = 100,
    ) -> List[LearningSignal]:
        """Get signals targeted for a specific engine.

        Args:
            engine: Target engine name
            region: Optional region filter
            limit: Max signals to return

        Returns:
            List of LearningSignal for the engine
        """
        signals = [
            s
            for s in self._signal_store.values()
            if s.target_engine in [engine, "all"] and not s.is_routed
        ]

        if region:
            signals = [s for s in signals if s.region_scope == region]

        # Sort by creation time, newest first
        signals = sorted(signals, key=lambda s: s.created_at, reverse=True)

        return signals[:limit]

    async def mark_routed(
        self,
        signal_ids: List[str],
        stream: str,
    ) -> int:
        """Mark signals as routed.

        Args:
            signal_ids: List of signal IDs
            stream: Stream they were routed to

        Returns:
            Count of signals updated
        """
        count = 0
        now = datetime.utcnow()

        for signal_id in signal_ids:
            signal = self._signal_store.get(signal_id)
            if signal:
                # Create updated signal (since LearningSignal is mostly immutable in practice)
                updated = LearningSignal(
                    **{
                        **signal.model_dump(),
                        "is_routed": True,
                        "routed_at": now,
                        "routing_stream": stream,
                    }
                )
                self._signal_store[signal_id] = updated
                count += 1

        logger.info(f"Marked {count} signals as routed to {stream}")
        return count

    async def get_unrouted_count(self, engine: Optional[str] = None) -> int:
        """Get count of unrouted signals.

        Args:
            engine: Optional engine filter

        Returns:
            Count of unrouted signals
        """
        signals = [s for s in self._signal_store.values() if not s.is_routed]

        if engine:
            signals = [s for s in signals if s.target_engine in [engine, "all"]]

        return len(signals)
