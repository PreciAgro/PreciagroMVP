"""ValidationService - Validates feedback before processing.

This service performs:
- Duplicate detection per recommendation
- Contradiction detection across time
- Noise detection based on farmer profile
- Region mismatch rejection
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass

from ..models.feedback_event import FeedbackEvent
from ..contracts.upstream import FarmerProfileContext
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of feedback validation."""

    is_valid: bool
    is_duplicate: bool = False
    duplicate_of_id: Optional[str] = None
    is_contradiction: bool = False
    contradiction_ids: List[str] = None
    is_noise: bool = False
    noise_reason: Optional[str] = None
    region_valid: bool = True
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.contradiction_ids is None:
            self.contradiction_ids = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class ValidationService:
    """Service for validating feedback before processing.

    Implements validation rules:
    - No duplicate feedback per recommendation within time window
    - Detects contradictions across time
    - Filters noise based on farmer profile patterns
    - Rejects region mismatches
    """

    def __init__(self):
        """Initialize validation service."""
        self._feedback_cache: dict = {}  # Cache for duplicate detection

    async def validate(
        self,
        event: FeedbackEvent,
        existing_events: List[FeedbackEvent],
        farmer_profile: Optional[FarmerProfileContext] = None,
    ) -> ValidationResult:
        """Validate a feedback event.

        Args:
            event: FeedbackEvent to validate
            existing_events: Existing events for same recommendation
            farmer_profile: Optional farmer profile context

        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []

        # Check region validity
        region_valid = self._validate_region(event)
        if not region_valid:
            errors.append(f"Invalid region code: {event.region_code}")
            return ValidationResult(
                is_valid=False,
                region_valid=False,
                errors=errors,
            )

        # Check for duplicates
        is_duplicate, duplicate_of = self._detect_duplicate(event, existing_events)
        if is_duplicate:
            warnings.append(f"Duplicate of feedback {duplicate_of}")

        # Check for contradictions
        is_contradiction, contradiction_ids = self._detect_contradictions(event, existing_events)
        if is_contradiction:
            warnings.append(f"Contradicts feedback: {contradiction_ids}")

        # Check for noise
        is_noise, noise_reason = self._detect_noise(event, farmer_profile)
        if is_noise:
            warnings.append(f"Classified as noise: {noise_reason}")

        # Determine overall validity
        is_valid = not is_duplicate and region_valid

        if not is_valid:
            errors.append("Feedback failed validation")

        return ValidationResult(
            is_valid=is_valid,
            is_duplicate=is_duplicate,
            duplicate_of_id=duplicate_of,
            is_contradiction=is_contradiction,
            contradiction_ids=contradiction_ids,
            is_noise=is_noise,
            noise_reason=noise_reason,
            region_valid=region_valid,
            errors=errors,
            warnings=warnings,
        )

    def _validate_region(self, event: FeedbackEvent) -> bool:
        """Validate region code.

        Args:
            event: FeedbackEvent to check

        Returns:
            True if region is valid
        """
        return event.region_code in settings.SUPPORTED_REGIONS

    def _detect_duplicate(
        self,
        event: FeedbackEvent,
        existing_events: List[FeedbackEvent],
    ) -> Tuple[bool, Optional[str]]:
        """Detect if feedback is a duplicate.

        Duplicates are detected within the configured time window
        for the same recommendation from the same user.

        Args:
            event: FeedbackEvent to check
            existing_events: Existing events to compare against

        Returns:
            Tuple of (is_duplicate, duplicate_of_id)
        """
        window = timedelta(hours=settings.DUPLICATE_WINDOW_HOURS)

        for existing in existing_events:
            # Same user, same type, within window
            if (
                existing.user_id == event.user_id
                and existing.feedback_type == event.feedback_type
                and existing.feedback_id != event.feedback_id
            ):
                time_diff = abs((event.created_at - existing.created_at).total_seconds())
                if time_diff < window.total_seconds():
                    # Check for similar content
                    if self._is_similar_content(event, existing):
                        logger.info(
                            f"Duplicate detected: {event.feedback_id} duplicates {existing.feedback_id}"
                        )
                        return True, existing.feedback_id

        return False, None

    def _is_similar_content(
        self,
        event: FeedbackEvent,
        existing: FeedbackEvent,
    ) -> bool:
        """Check if two feedback events have similar content.

        Args:
            event: New event
            existing: Existing event

        Returns:
            True if content is similar
        """
        # For explicit feedback, compare ratings and categories
        if event.feedback_type == "explicit":
            if event.rating == existing.rating:
                if event.feedback_category == existing.feedback_category:
                    return True

        # For implicit feedback, compare key signals
        elif event.feedback_type == "implicit":
            if (
                event.clicked_action == existing.clicked_action
                and event.dismissed == existing.dismissed
            ):
                return True

        # For outcome feedback, compare outcome category
        elif event.feedback_type == "outcome":
            if event.outcome_category == existing.outcome_category:
                return True

        return False

    def _detect_contradictions(
        self,
        event: FeedbackEvent,
        existing_events: List[FeedbackEvent],
    ) -> Tuple[bool, List[str]]:
        """Detect contradicting feedback.

        Contradictions are feedback from the same user that
        conflicts with previous feedback within the window.

        Args:
            event: FeedbackEvent to check
            existing_events: Existing events to compare against

        Returns:
            Tuple of (has_contradictions, contradiction_ids)
        """
        window = timedelta(days=settings.CONTRADICTION_WINDOW_DAYS)
        contradictions = []

        for existing in existing_events:
            # Same user, within window
            if existing.user_id == event.user_id:
                time_diff = abs((event.created_at - existing.created_at).total_seconds())
                if time_diff < window.total_seconds():
                    if self._is_contradicting(event, existing):
                        contradictions.append(existing.feedback_id)

        if contradictions:
            logger.info(f"Contradictions detected for {event.feedback_id}: {contradictions}")

        return len(contradictions) > 0, contradictions

    def _is_contradicting(
        self,
        event: FeedbackEvent,
        existing: FeedbackEvent,
    ) -> bool:
        """Check if two feedback events contradict each other.

        Args:
            event: New event
            existing: Existing event

        Returns:
            True if events contradict
        """
        # For explicit feedback, significant rating difference
        if event.feedback_type == "explicit" and existing.feedback_type == "explicit":
            if event.rating and existing.rating:
                # Rating difference of 3+ is a contradiction
                if abs(event.rating - existing.rating) >= 3:
                    return True
                # Opposite categories
                positive = {"helpful"}
                negative = {"not_helpful", "incorrect"}
                if (
                    event.feedback_category in positive and existing.feedback_category in negative
                ) or (
                    event.feedback_category in negative and existing.feedback_category in positive
                ):
                    return True

        # For implicit feedback, action vs dismiss
        if event.feedback_type == "implicit" and existing.feedback_type == "implicit":
            if event.clicked_action and existing.dismissed:
                return True
            if event.dismissed and existing.clicked_action:
                return True

        # For outcome feedback, opposite outcomes
        if event.feedback_type == "outcome" and existing.feedback_type == "outcome":
            positive_outcomes = {"success", "partial_success"}
            negative_outcomes = {"negative_effect"}
            if (
                event.outcome_category in positive_outcomes
                and existing.outcome_category in negative_outcomes
            ) or (
                event.outcome_category in negative_outcomes
                and existing.outcome_category in positive_outcomes
            ):
                return True

        return False

    def _detect_noise(
        self,
        event: FeedbackEvent,
        farmer_profile: Optional[FarmerProfileContext],
    ) -> Tuple[bool, Optional[str]]:
        """Detect if feedback is noise based on farmer profile.

        Noise detection uses:
        - Historical accuracy of farmer
        - Engagement patterns
        - Trust indicators

        Args:
            event: FeedbackEvent to check
            farmer_profile: Optional farmer context

        Returns:
            Tuple of (is_noise, reason)
        """
        if not farmer_profile:
            # Without profile, can't determine noise
            return False, None

        # Low accuracy farmers with extreme ratings
        if farmer_profile.historical_accuracy:
            if farmer_profile.historical_accuracy < 0.3:
                if event.rating in [1, 5]:  # Extreme ratings
                    return True, "Low accuracy farmer with extreme rating"

        # Very low engagement with high rating
        if farmer_profile.engagement_score:
            if farmer_profile.engagement_score < 0.2:
                if event.rating and event.rating >= 5:
                    return True, "Very low engagement with max rating"

        # Unverified identity with correction suggestion
        if not farmer_profile.verified_identity:
            if event.feedback_type == "explicit":
                raw = event.raw_payload
                if raw.get("suggested_correction"):
                    return True, "Unverified identity providing corrections"

        return False, None

    async def validate_batch(
        self,
        events: List[FeedbackEvent],
        farmer_profiles: dict[str, FarmerProfileContext] = None,
    ) -> List[Tuple[FeedbackEvent, ValidationResult]]:
        """Validate a batch of feedback events.

        Args:
            events: List of events to validate
            farmer_profiles: Map of user_id to profile

        Returns:
            List of (event, result) tuples
        """
        farmer_profiles = farmer_profiles or {}
        results = []

        # Group by recommendation for duplicate detection
        by_recommendation = {}
        for event in events:
            rec_id = event.recommendation_id
            if rec_id not in by_recommendation:
                by_recommendation[rec_id] = []
            by_recommendation[rec_id].append(event)

        for event in events:
            existing = [
                e
                for e in by_recommendation[event.recommendation_id]
                if e.feedback_id != event.feedback_id
            ]
            profile = farmer_profiles.get(event.user_id)

            result = await self.validate(event, existing, profile)
            results.append((event, result))

        return results
