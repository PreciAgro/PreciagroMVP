"""Constraint & Safety Engine - Enforces constraints and safety rules."""

import logging
from typing import List, Dict, Any, Tuple

from ..models.domain import (
    Recommendation,
    RecommendationPlan,
    ConstraintViolation,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class ConstraintSafetyEngine:
    """Enforces inventory, legality, crop safety, environmental risk, and farmer constraints."""

    def __init__(self):
        """Initialize the constraint and safety engine."""
        self._safety_rules = self._build_safety_rules()
        self._constraint_rules = self._build_constraint_rules()

    def validate_plan(
        self, plan: RecommendationPlan, context: Dict[str, Any]
    ) -> Tuple[RecommendationPlan, List[ConstraintViolation]]:
        """
        Validate recommendation plan against constraints and safety rules.

        Args:
            plan: Recommendation plan to validate
            context: Contextual information (inventory, regulations, etc.)

        Returns:
            Tuple of (validated plan, constraint violations)
        """
        violations = []

        for recommendation in plan.recommendations:
            # Check inventory constraints
            inv_violations = self._check_inventory_constraints(recommendation, context)
            violations.extend(inv_violations)

            # Check legality constraints
            legal_violations = self._check_legality_constraints(recommendation, context)
            violations.extend(legal_violations)

            # Check crop safety constraints
            safety_violations = self._check_crop_safety_constraints(recommendation, context)
            violations.extend(safety_violations)

            # Check environmental risk constraints
            env_violations = self._check_environmental_risk_constraints(recommendation, context)
            violations.extend(env_violations)

            # Check farmer constraints
            farmer_violations = self._check_farmer_constraints(recommendation, context)
            violations.extend(farmer_violations)

            # Check temporal constraints
            temporal_violations = self._check_temporal_constraints(recommendation, context)
            violations.extend(temporal_violations)

            # Check spatial constraints
            spatial_violations = self._check_spatial_constraints(recommendation, context)
            violations.extend(spatial_violations)

        # Filter recommendations based on violations
        if violations:
            blocking_violations = [v for v in violations if v.severity == "blocking"]

            if blocking_violations:
                # Remove recommendations with blocking violations
                valid_recommendations = [
                    rec
                    for rec in plan.recommendations
                    if not any(
                        v.recommendation_id == rec.id and v.severity == "blocking"
                        for v in blocking_violations
                    )
                ]

                plan.recommendations = valid_recommendations
                plan.execution_order = [rec.id for rec in valid_recommendations]
                plan.validation_errors = [v.message for v in blocking_violations]
            else:
                # Add warnings but keep recommendations
                for rec in plan.recommendations:
                    rec_warnings = [v.message for v in violations if v.recommendation_id == rec.id]
                    rec.warnings.extend(rec_warnings)

        plan.is_validated = len([v for v in violations if v.severity == "blocking"]) == 0

        logger.info(
            f"Validated plan: {len(violations)} violations, "
            f"{len([v for v in violations if v.severity == 'blocking'])} blocking"
        )

        return plan, violations

    def _check_inventory_constraints(
        self, recommendation: Recommendation, context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Check inventory availability constraints."""
        violations = []

        if not settings.ENABLE_CONSTRAINT_CHECKING:
            return violations

        inventory = context.get("inventory", {})
        available_inputs = inventory.get("available_inputs", {})

        # Check if required inputs are available
        if recommendation.dosage:
            required_inputs = recommendation.dosage.get("required_inputs", [])

            for input_name in required_inputs:
                if input_name not in available_inputs:
                    violations.append(
                        ConstraintViolation(
                            constraint_type="inventory",
                            severity="error",
                            message=f"Required input '{input_name}' not available in inventory",
                            recommendation_id=recommendation.id,
                            details={"input_name": input_name},
                        )
                    )
                else:
                    input_data = available_inputs[input_name]
                    quantity = input_data.get("quantity", 0.0)

                    if quantity <= 0:
                        violations.append(
                            ConstraintViolation(
                                constraint_type="inventory",
                                severity="error",
                                message=f"Insufficient stock of '{input_name}' in inventory",
                                recommendation_id=recommendation.id,
                                details={"input_name": input_name, "available": quantity},
                            )
                        )

        return violations

    def _check_legality_constraints(
        self, recommendation: Recommendation, context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Check legal and regulatory constraints."""
        violations = []

        if not settings.ENABLE_CONSTRAINT_CHECKING:
            return violations

        region_code = context.get("region_code")
        regulations = context.get("regulations", {})

        # Check banned chemicals
        if recommendation.dosage:
            chemical_name = recommendation.dosage.get("chemical")
            if chemical_name:
                banned_chemicals = regulations.get("banned_chemicals", [])

                if chemical_name in banned_chemicals:
                    violations.append(
                        ConstraintViolation(
                            constraint_type="legality",
                            severity="blocking",
                            message=f"Chemical '{chemical_name}' is banned in region {region_code}",
                            recommendation_id=recommendation.id,
                            details={"chemical": chemical_name, "region": region_code},
                        )
                    )

        # Check application timing restrictions
        timing_restrictions = regulations.get("timing_restrictions", {})
        if recommendation.timing:
            for restriction in timing_restrictions:
                if restriction.get("applies_to") == recommendation.type.value:
                    violations.append(
                        ConstraintViolation(
                            constraint_type="legality",
                            severity="warning",
                            message=f"Timing restriction applies: {restriction.get('reason')}",
                            recommendation_id=recommendation.id,
                            details=restriction,
                        )
                    )

        return violations

    def _check_crop_safety_constraints(
        self, recommendation: Recommendation, context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Check crop safety constraints."""
        violations = []

        if not settings.ENABLE_SAFETY_VALIDATION:
            return violations

        crop_type = context.get("crop_type")
        growth_stage = context.get("growth_stage")

        # Check crop-chemical compatibility
        if recommendation.dosage:
            chemical_name = recommendation.dosage.get("chemical")
            if chemical_name:
                crop_safety = context.get("crop_safety", {})
                incompatible_chemicals = crop_safety.get("incompatible_chemicals", {})

                if crop_type in incompatible_chemicals:
                    if chemical_name in incompatible_chemicals[crop_type]:
                        violations.append(
                            ConstraintViolation(
                                constraint_type="crop_safety",
                                severity="blocking",
                                message=f"Chemical '{chemical_name}' is not safe for {crop_type}",
                                recommendation_id=recommendation.id,
                                details={"chemical": chemical_name, "crop": crop_type},
                            )
                        )

        # Check growth stage restrictions
        if growth_stage:
            stage_restrictions = context.get("growth_stage_restrictions", {})
            if growth_stage in stage_restrictions:
                restricted_actions = stage_restrictions[growth_stage]
                if recommendation.type.value in restricted_actions:
                    violations.append(
                        ConstraintViolation(
                            constraint_type="crop_safety",
                            severity="warning",
                            message=f"Action not recommended during {growth_stage} stage",
                            recommendation_id=recommendation.id,
                            details={
                                "growth_stage": growth_stage,
                                "action": recommendation.type.value,
                            },
                        )
                    )

        return violations

    def _check_environmental_risk_constraints(
        self, recommendation: Recommendation, context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Check environmental risk constraints."""
        violations = []

        if not settings.ENABLE_SAFETY_VALIDATION:
            return violations

        weather = context.get("weather", {})
        forecast = weather.get("forecast", {})

        # Check weather conditions for application
        if recommendation.type.value in ["treatment", "nutrient_application"]:
            if forecast.get("rain_expected", False):
                violations.append(
                    ConstraintViolation(
                        constraint_type="environmental_risk",
                        severity="warning",
                        message="Rain expected - delay application to avoid wash-off",
                        recommendation_id=recommendation.id,
                        details={"forecast": forecast},
                    )
                )

            if forecast.get("wind_speed", 0) > 15:  # km/h
                violations.append(
                    ConstraintViolation(
                        constraint_type="environmental_risk",
                        severity="warning",
                        message="High wind conditions - delay application to avoid drift",
                        recommendation_id=recommendation.id,
                        details={"wind_speed": forecast.get("wind_speed")},
                    )
                )

        return violations

    def _check_farmer_constraints(
        self, recommendation: Recommendation, context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Check farmer preferences and constraints."""
        violations = []

        farmer_profile = context.get("farmer_profile", {})
        preferences = farmer_profile.get("preferences", {})
        constraints = farmer_profile.get("constraints", {})
        budget_class = farmer_profile.get("budget_class", "medium")

        # Check budget constraints
        if recommendation.cost_estimate:
            cost_range = recommendation.cost_estimate.get("range", "")
            if cost_range:
                try:
                    max_cost = float(cost_range.split("-")[1].split()[0])
                    budget_limits = {"low": 100, "medium": 300, "high": 1000}
                    budget_limit = budget_limits.get(budget_class, 300)

                    if max_cost > budget_limit:
                        violations.append(
                            ConstraintViolation(
                                constraint_type="farmer_preference",
                                severity="warning",
                                message=f"Recommendation cost ({max_cost}) exceeds budget class limit ({budget_limit})",
                                recommendation_id=recommendation.id,
                                details={"cost": max_cost, "budget_limit": budget_limit},
                            )
                        )
                except (ValueError, IndexError):
                    pass

        # Check organic preferences
        if preferences.get("organic_only", False):
            if recommendation.dosage and recommendation.dosage.get("chemical"):
                violations.append(
                    ConstraintViolation(
                        constraint_type="farmer_preference",
                        severity="error",
                        message="Chemical treatment conflicts with organic farming preference",
                        recommendation_id=recommendation.id,
                        details={"preference": "organic_only"},
                    )
                )

        return violations

    def _check_temporal_constraints(
        self, recommendation: Recommendation, context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Check temporal constraints."""
        violations = []

        current_season = context.get("current_season")
        growth_stage = context.get("growth_stage")

        # Check season compatibility
        if recommendation.timing:
            # Simple heuristic: some actions are season-specific
            if "harvest" in recommendation.title.lower() and current_season != "harvest":
                violations.append(
                    ConstraintViolation(
                        constraint_type="temporal",
                        severity="warning",
                        message="Harvest action may not be appropriate for current season",
                        recommendation_id=recommendation.id,
                        details={"current_season": current_season},
                    )
                )

        return violations

    def _check_spatial_constraints(
        self, recommendation: Recommendation, context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Check spatial constraints."""
        violations = []

        region_code = context.get("region_code")

        # Check region-specific restrictions
        if region_code:
            region_restrictions = context.get("region_restrictions", {})
            if region_code in region_restrictions:
                restricted_actions = region_restrictions[region_code]
                if recommendation.type.value in restricted_actions:
                    violations.append(
                        ConstraintViolation(
                            constraint_type="spatial",
                            severity="warning",
                            message=f"Action restricted in region {region_code}",
                            recommendation_id=recommendation.id,
                            details={"region": region_code},
                        )
                    )

        return violations

    def _build_safety_rules(self) -> Dict[str, Any]:
        """Build safety rules."""
        return {
            "max_wind_speed_kmh": 15,
            "min_temperature_c": 5,
            "max_temperature_c": 35,
            "rain_delay_hours": 24,
        }

    def _build_constraint_rules(self) -> Dict[str, Any]:
        """Build constraint rules."""
        return {
            "min_inventory_threshold": 0.1,
            "budget_multiplier": 1.2,
        }
