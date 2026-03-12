"""Safety & Domain Constraint Engine."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..contracts.v1.schemas import FarmerRequest, AgroLLMResponse, RecommendedAction

logger = logging.getLogger(__name__)


class ViolationSeverity(str, Enum):
    """Severity of constraint violation."""

    BLOCKING = "blocking"  # Must reject
    WARNING = "warning"  # Can proceed with warning
    INFO = "info"  # Informational only


@dataclass
class ConstraintViolation:
    """Constraint violation record."""

    type: str
    severity: ViolationSeverity
    message: str
    field: Optional[str] = None
    suggested_fix: Optional[str] = None


class SafetyConstraintEngine:
    """Engine for validating safety and domain constraints."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize safety constraint engine.

        Args:
            config: Configuration dictionary with safety rules
        """
        self.config = config or {}
        self.banned_chemicals = self.config.get("banned_chemicals", [])
        self.season_rules = self.config.get("season_rules", {})
        self.soil_crop_compatibility = self.config.get("soil_crop_compatibility", {})
        self.weather_constraints = self.config.get("weather_constraints", {})

        logger.info("SafetyConstraintEngine initialized")

    def validate_request(self, request: FarmerRequest) -> List[ConstraintViolation]:
        """Validate incoming request for safety constraints.

        Args:
            request: Farmer request to validate

        Returns:
            List of constraint violations
        """
        violations = []

        # Validate soil × crop compatibility
        if request.soil and request.crop:
            violations.extend(self._check_soil_crop_compatibility(request.soil, request.crop))

        # Validate season compatibility
        if request.crop:
            violations.extend(
                self._check_season_compatibility(request.crop, request.geo.region_code)
            )

        # Validate weather constraints
        if request.weather:
            violations.extend(self._check_weather_constraints(request.weather, request.crop))

        return violations

    def validate_response(
        self, response: AgroLLMResponse, request: FarmerRequest
    ) -> List[ConstraintViolation]:
        """Validate LLM response for safety constraints.

        Args:
            response: LLM response to validate
            request: Original request context

        Returns:
            List of constraint violations
        """
        violations = []

        # Check recommended actions
        for action in response.diagnosis_card.recommended_actions:
            violations.extend(self._check_action_safety(action, request))

        # Check for banned chemicals in recommendations
        violations.extend(self._check_banned_chemicals(response, request))

        # Check warnings
        if not response.diagnosis_card.warnings:
            # If high severity but no warnings, flag it
            if response.diagnosis_card.severity == "high":
                violations.append(
                    ConstraintViolation(
                        type="missing_warning",
                        severity=ViolationSeverity.WARNING,
                        message="High severity diagnosis should include warnings",
                        field="diagnosis_card.warnings",
                    )
                )

        return violations

    def _check_soil_crop_compatibility(self, soil: Any, crop: Any) -> List[ConstraintViolation]:
        """Check soil × crop compatibility."""
        violations = []

        # Get compatibility rules for crop type
        crop_type = crop.type.lower()
        compatibility_rules = self.soil_crop_compatibility.get(crop_type, {})

        # Check pH range
        if soil.pH is not None:
            optimal_ph_range = compatibility_rules.get("optimal_ph_range", (6.0, 7.0))
            if not (optimal_ph_range[0] <= soil.pH <= optimal_ph_range[1]):
                violations.append(
                    ConstraintViolation(
                        type="ph_incompatibility",
                        severity=ViolationSeverity.WARNING,
                        message=f"pH {soil.pH} may not be optimal for {crop_type} (optimal: {optimal_ph_range[0]}-{optimal_ph_range[1]})",
                        field="soil.pH",
                        suggested_fix=f"Consider soil amendment to adjust pH to {optimal_ph_range[0]}-{optimal_ph_range[1]}",
                    )
                )

        # Check moisture requirements
        if soil.moisture is not None:
            optimal_moisture = compatibility_rules.get("optimal_moisture_range", (30.0, 70.0))
            if not (optimal_moisture[0] <= soil.moisture <= optimal_moisture[1]):
                violations.append(
                    ConstraintViolation(
                        type="moisture_incompatibility",
                        severity=ViolationSeverity.INFO,
                        message=f"Moisture {soil.moisture}% may not be optimal for {crop_type}",
                        field="soil.moisture",
                    )
                )

        return violations

    def _check_season_compatibility(self, crop: Any, region_code: str) -> List[ConstraintViolation]:
        """Check season compatibility for crop and region."""
        violations = []

        # Get season rules for region
        region_rules = self.season_rules.get(region_code, {})
        crop_seasons = region_rules.get(crop.type.lower(), [])

        # For MVP, we'll use a simple check
        # In production, this would check actual current season
        if crop_seasons and len(crop_seasons) > 0:
            # Placeholder: assume we can check if current time is in planting season
            # For now, just log
            logger.debug(f"Checking season compatibility for {crop.type} in {region_code}")

        return violations

    def _check_weather_constraints(
        self, weather: Any, crop: Optional[Any]
    ) -> List[ConstraintViolation]:
        """Check weather constraints."""
        violations = []

        # Check temperature extremes
        if weather.temp is not None:
            temp_constraints = self.weather_constraints.get("temperature", {})
            min_temp = temp_constraints.get("min", 0.0)
            max_temp = temp_constraints.get("max", 45.0)

            if weather.temp < min_temp:
                violations.append(
                    ConstraintViolation(
                        type="temperature_too_low",
                        severity=ViolationSeverity.WARNING,
                        message=f"Temperature {weather.temp}°C is below recommended minimum {min_temp}°C",
                        field="weather.temp",
                    )
                )
            elif weather.temp > max_temp:
                violations.append(
                    ConstraintViolation(
                        type="temperature_too_high",
                        severity=ViolationSeverity.WARNING,
                        message=f"Temperature {weather.temp}°C exceeds recommended maximum {max_temp}°C",
                        field="weather.temp",
                    )
                )

        return violations

    def _check_action_safety(
        self, action: RecommendedAction, request: FarmerRequest
    ) -> List[ConstraintViolation]:
        """Check individual action for safety."""
        violations = []

        action_lower = action.action.lower()

        # Check for dangerous actions
        dangerous_keywords = ["pesticide", "herbicide", "fungicide"]
        if any(keyword in action_lower for keyword in dangerous_keywords):
            # Ensure proper safety warnings
            if not any(
                "safety" in w.lower() or "protective" in w.lower()
                for w in request.session_context[-1].previous_response.split()
                if request.session_context
            ):
                violations.append(
                    ConstraintViolation(
                        type="missing_safety_warning",
                        severity=ViolationSeverity.WARNING,
                        message=f"Chemical application action should include safety warnings",
                        field="action",
                        suggested_fix="Add safety warnings about protective equipment",
                    )
                )

        return violations

    def _check_banned_chemicals(
        self, response: AgroLLMResponse, request: FarmerRequest
    ) -> List[ConstraintViolation]:
        """Check for banned chemicals in recommendations."""
        violations = []

        # Check all text for banned chemicals
        all_text = (
            response.generated_text
            + " "
            + " ".join(a.action for a in response.diagnosis_card.recommended_actions)
            + " "
            + " ".join(response.diagnosis_card.warnings)
        ).lower()

        for banned in self.banned_chemicals:
            if banned.lower() in all_text:
                violations.append(
                    ConstraintViolation(
                        type="banned_chemical",
                        severity=ViolationSeverity.BLOCKING,
                        message=f"Banned chemical '{banned}' detected in recommendations",
                        field="recommended_actions",
                        suggested_fix=f"Remove or replace recommendation containing '{banned}'",
                    )
                )

        return violations
