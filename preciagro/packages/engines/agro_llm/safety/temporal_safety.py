"""Temporal Safety Validators - PHI, season, crop stage checks."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .constraint_engine import ConstraintViolation, ViolationSeverity

logger = logging.getLogger(__name__)


@dataclass
class PHIRule:
    """Pre-Harvest Interval (PHI) rule."""

    chemical: str
    crop: str
    days: int  # Minimum days before harvest
    description: Optional[str] = None


@dataclass
class CropStageRule:
    """Crop stage compatibility rule."""

    crop: str
    growth_stage: str
    allowed_actions: List[str]
    prohibited_actions: List[str]
    description: Optional[str] = None


class TemporalSafetyValidator:
    """Validates temporal safety constraints."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize temporal safety validator.

        Args:
            config: Configuration with PHI rules, crop stage rules, etc.
        """
        self.config = config or {}
        self.phi_rules = self._load_phi_rules()
        self.crop_stage_rules = self._load_crop_stage_rules()
        self.season_rules = self.config.get("season_rules", {})

        logger.info("TemporalSafetyValidator initialized")

    def validate(
        self, response: Any, request: Any, current_date: Optional[datetime] = None
    ) -> List[ConstraintViolation]:
        """Validate temporal safety constraints.

        Args:
            response: LLM response
            request: Original request
            current_date: Current date (defaults to now)

        Returns:
            List of constraint violations
        """
        if current_date is None:
            current_date = datetime.utcnow()

        violations = []

        # Check PHI violations
        if request.crop and hasattr(request, "geo"):
            violations.extend(self._check_phi_violations(response, request, current_date))

        # Check crop stage compatibility
        if request.crop:
            violations.extend(self._check_crop_stage_compatibility(response, request))

        # Check season compatibility
        violations.extend(self._check_season_compatibility(response, request, current_date))

        # Check "too late in season"
        violations.extend(self._check_too_late_in_season(response, request, current_date))

        return violations

    def _check_phi_violations(
        self, response: Any, request: Any, current_date: datetime
    ) -> List[ConstraintViolation]:
        """Check Pre-Harvest Interval violations."""
        violations = []

        crop_type = request.crop.type.lower() if request.crop else None
        if not crop_type:
            return violations

        # Get expected harvest date (if available)
        harvest_date = self._estimate_harvest_date(request, current_date)
        if not harvest_date:
            return violations

        # Check each recommended action
        for action in response.diagnosis_card.recommended_actions:
            action_text = action.action.lower()

            # Check against PHI rules
            for phi_rule in self.phi_rules:
                if phi_rule.crop.lower() == crop_type and phi_rule.chemical.lower() in action_text:

                    days_until_harvest = (harvest_date - current_date).days

                    if days_until_harvest < phi_rule.days:
                        violations.append(
                            ConstraintViolation(
                                type="phi_violation",
                                severity=ViolationSeverity.BLOCKING,
                                message=(
                                    f"PHI violation: {phi_rule.chemical} requires "
                                    f"{phi_rule.days} days before harvest, but only "
                                    f"{days_until_harvest} days remaining"
                                ),
                                field="recommended_actions",
                                suggested_fix=(
                                    f"Do not apply {phi_rule.chemical} - insufficient time "
                                    f"before harvest. Use alternative treatment or delay harvest."
                                ),
                            )
                        )

        return violations

    def _check_crop_stage_compatibility(
        self, response: Any, request: Any
    ) -> List[ConstraintViolation]:
        """Check crop stage compatibility with recommendations."""
        violations = []

        crop_type = request.crop.type.lower() if request.crop else None
        growth_stage = (
            request.crop.growth_stage.lower()
            if (request.crop and request.crop.growth_stage)
            else None
        )

        if not crop_type or not growth_stage:
            return violations

        # Find matching crop stage rule
        matching_rule = None
        for rule in self.crop_stage_rules:
            if rule.crop.lower() == crop_type and rule.growth_stage.lower() == growth_stage:
                matching_rule = rule
                break

        if not matching_rule:
            return violations

        # Check each action
        for action in response.diagnosis_card.recommended_actions:
            action_text = action.action.lower()

            # Check if action is prohibited for this stage
            for prohibited in matching_rule.prohibited_actions:
                if prohibited.lower() in action_text:
                    violations.append(
                        ConstraintViolation(
                            type="crop_stage_incompatible",
                            severity=ViolationSeverity.WARNING,
                            message=(
                                f"Action '{action.action}' is not recommended for "
                                f"{crop_type} at {growth_stage} stage"
                            ),
                            field="recommended_actions",
                            suggested_fix=(
                                f"Wait until appropriate growth stage or use alternative action"
                            ),
                        )
                    )

        return violations

    def _check_season_compatibility(
        self, response: Any, request: Any, current_date: datetime
    ) -> List[ConstraintViolation]:
        """Check season compatibility."""
        violations = []

        # Get current season
        current_season = self._get_current_season(request, current_date)
        if not current_season:
            return violations

        # Check if recommendations are season-appropriate
        # This is a simplified check - in production, would use detailed season rules
        season_rules = self.season_rules.get(current_season, {})

        if season_rules:
            for action in response.diagnosis_card.recommended_actions:
                action_type = self._classify_action_type(action.action)
                if action_type in season_rules.get("prohibited_actions", []):
                    violations.append(
                        ConstraintViolation(
                            type="season_incompatible",
                            severity=ViolationSeverity.WARNING,
                            message=(
                                f"Action '{action.action}' is not recommended "
                                f"during {current_season} season"
                            ),
                            field="recommended_actions",
                        )
                    )

        return violations

    def _check_too_late_in_season(
        self, response: Any, request: Any, current_date: datetime
    ) -> List[ConstraintViolation]:
        """Check if it's too late in season for recommendations."""
        violations = []

        crop_type = request.crop.type.lower() if request.crop else None
        if not crop_type:
            return violations

        # Estimate if we're too late in the growing season
        # This is simplified - in production, would use crop calendars
        planting_date = None
        if request.crop and request.crop.planting_date:
            try:
                planting_date = datetime.fromisoformat(
                    request.crop.planting_date.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        if planting_date:
            days_since_planting = (current_date - planting_date).days

            # Rough estimate: if > 120 days for most crops, might be too late
            # This should be crop-specific
            if days_since_planting > 120:
                # Check if action is time-sensitive
                for action in response.diagnosis_card.recommended_actions:
                    time_sensitive_keywords = ["planting", "sowing", "transplanting", "early stage"]
                    if any(keyword in action.action.lower() for keyword in time_sensitive_keywords):
                        violations.append(
                            ConstraintViolation(
                                type="too_late_in_season",
                                severity=ViolationSeverity.WARNING,
                                message=(
                                    f"Action '{action.action}' may be too late in the season "
                                    f"({days_since_planting} days since planting)"
                                ),
                                field="recommended_actions",
                            )
                        )

        return violations

    def _estimate_harvest_date(self, request: Any, current_date: datetime) -> Optional[datetime]:
        """Estimate harvest date based on crop and planting date."""
        if not request.crop or not request.crop.planting_date:
            return None

        try:
            planting_date = datetime.fromisoformat(
                request.crop.planting_date.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            return None

        crop_type = request.crop.type.lower()

        # Rough harvest date estimates (days to maturity)
        # In production, use detailed crop calendars
        maturity_days = {
            "maize": 90,
            "rice": 120,
            "wheat": 100,
            "soybean": 90,
        }

        days_to_maturity = maturity_days.get(crop_type, 100)
        harvest_date = planting_date + timedelta(days=days_to_maturity)

        return harvest_date

    def _get_current_season(self, request: Any, current_date: datetime) -> Optional[str]:
        """Get current season based on region and date."""
        # Simplified season detection
        # In production, use region-specific calendars
        month = current_date.month

        # Northern hemisphere seasons (adjust for region)
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    def _classify_action_type(self, action_text: str) -> str:
        """Classify action type."""
        action_lower = action_text.lower()

        if any(kw in action_lower for kw in ["plant", "sow", "transplant"]):
            return "planting"
        elif any(kw in action_lower for kw in ["fertilize", "nutrient", "nitrogen"]):
            return "fertilization"
        elif any(kw in action_lower for kw in ["pesticide", "herbicide", "spray"]):
            return "chemical_application"
        elif any(kw in action_lower for kw in ["irrigate", "water"]):
            return "irrigation"
        else:
            return "other"

    def _load_phi_rules(self) -> List[PHIRule]:
        """Load PHI rules from config."""
        phi_data = self.config.get("phi_rules", [])
        rules = []

        for rule_data in phi_data:
            if isinstance(rule_data, dict):
                rules.append(
                    PHIRule(
                        chemical=rule_data.get("chemical", ""),
                        crop=rule_data.get("crop", ""),
                        days=rule_data.get("days", 0),
                        description=rule_data.get("description"),
                    )
                )

        # Default PHI rules if none provided
        if not rules:
            rules = [
                PHIRule(chemical="pesticide", crop="maize", days=21),
                PHIRule(chemical="herbicide", crop="maize", days=14),
                PHIRule(chemical="fungicide", crop="maize", days=7),
            ]

        return rules

    def _load_crop_stage_rules(self) -> List[CropStageRule]:
        """Load crop stage rules from config."""
        stage_data = self.config.get("crop_stage_rules", [])
        rules = []

        for rule_data in stage_data:
            if isinstance(rule_data, dict):
                rules.append(
                    CropStageRule(
                        crop=rule_data.get("crop", ""),
                        growth_stage=rule_data.get("growth_stage", ""),
                        allowed_actions=rule_data.get("allowed_actions", []),
                        prohibited_actions=rule_data.get("prohibited_actions", []),
                        description=rule_data.get("description"),
                    )
                )

        return rules
