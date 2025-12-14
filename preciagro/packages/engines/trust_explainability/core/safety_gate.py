"""Safety Gate Module.

Pre-action safety and compliance validation.
Blocks, downgrades, or flags unsafe outputs before they reach users.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..contracts.v1.schemas import SafetyCheckResult, SafetyViolation
from ..contracts.v1.enums import SafetyStatus, ViolationSeverity
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class SafetyGate:
    """Pre-action safety and compliance validation.
    
    Validates recommendations against:
    - Compliance rules (regional regulations)
    - Safety limits (chemicals, dosages, timing)
    - Inventory constraints
    - Economic feasibility
    """
    
    def __init__(self) -> None:
        """Initialize safety gate."""
        self.settings = get_settings()
        
        # Safety limits database (in production: load from config/database)
        self._dosage_limits: Dict[str, Dict[str, float]] = {
            # Chemical: {min_rate_per_hectare, max_rate_per_hectare}
            "glyphosate": {"min": 0.5, "max": 4.0, "unit": "L/ha"},
            "chlorpyrifos": {"min": 0.5, "max": 2.0, "unit": "L/ha"},
            "copper_sulfate": {"min": 1.0, "max": 6.0, "unit": "kg/ha"},
            "neem_oil": {"min": 2.0, "max": 10.0, "unit": "ml/L"},
        }
        
        # Timing constraints
        self._timing_constraints: Dict[str, Dict[str, Any]] = {
            "pesticide": {
                "pre_harvest_days": 14,
                "min_reentry_hours": 24,
            },
            "fungicide": {
                "pre_harvest_days": 7,
                "min_reentry_hours": 12,
            },
            "fertilizer": {
                "pre_harvest_days": 0,
                "min_reentry_hours": 0,
            },
        }
    
    def validate(
        self,
        recommendation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Validate a recommendation against all safety rules.
        
        Args:
            recommendation: Recommendation to validate
            context: Context including region, crop, inventory, etc.
            
        Returns:
            SafetyCheckResult with status and any violations
        """
        violations: List[SafetyViolation] = []
        
        # Run all checks
        region = context.get("region", context.get("region_code"))
        
        # 1. Compliance check
        if region:
            compliance_violations = self.check_compliance(
                recommendation, region
            )
            violations.extend(compliance_violations)
        
        # 2. Safety limits check
        safety_violations = self.check_safety_limits(recommendation)
        violations.extend(safety_violations)
        
        # 3. Inventory check
        inventory = context.get("inventory", {})
        if inventory:
            inventory_violations = self.check_inventory(recommendation, inventory)
            violations.extend(inventory_violations)
        
        # 4. Timing check
        crop_info = context.get("crop_info", context.get("crop", {}))
        if isinstance(crop_info, dict):
            timing_violations = self.check_timing(recommendation, crop_info)
            violations.extend(timing_violations)
        
        # Determine overall status
        blocking_count = sum(1 for v in violations if v.severity == ViolationSeverity.BLOCKING)
        warning_count = sum(1 for v in violations if v.severity == ViolationSeverity.WARNING)
        info_count = sum(1 for v in violations if v.severity == ViolationSeverity.INFO)
        
        if blocking_count > 0:
            status = SafetyStatus.BLOCKED
        elif warning_count > 0:
            status = SafetyStatus.WARNING
        else:
            status = SafetyStatus.PASSED
        
        return SafetyCheckResult(
            status=status,
            violations=violations,
            blocking_count=blocking_count,
            warning_count=warning_count,
            info_count=info_count,
            compliance_checked=region is not None,
            safety_limits_checked=True,
            inventory_checked=bool(inventory),
            region_code=region,
            checked_at=datetime.utcnow()
        )
    
    def check_compliance(
        self,
        recommendation: Dict[str, Any],
        region: str
    ) -> List[SafetyViolation]:
        """Check recommendation against regional compliance rules.
        
        Args:
            recommendation: Recommendation to check
            region: Region code
            
        Returns:
            List of compliance violations
        """
        violations: List[SafetyViolation] = []
        
        # Extract action text
        action_text = self._get_action_text(recommendation).lower()
        
        # Check for banned chemicals
        for chemical in self.settings.banned_chemicals:
            if chemical.lower() in action_text:
                violations.append(SafetyViolation(
                    violation_type="banned_chemical",
                    severity=ViolationSeverity.BLOCKING,
                    message=f"Chemical '{chemical}' is banned and cannot be recommended",
                    field="action",
                    suggested_fix=f"Remove or replace recommendation containing '{chemical}'",
                    can_override=False,
                    rule_id=f"compliance.banned.{chemical.lower()}"
                ))
        
        # Region-specific restrictions (example: Zimbabwe)
        if region and region.startswith("ZW"):
            # Check for restricted chemicals in Zimbabwe
            zw_restricted = ["carbofuran", "monocrotophos", "methamidophos"]
            for chemical in zw_restricted:
                if chemical in action_text:
                    violations.append(SafetyViolation(
                        violation_type="region_restricted",
                        severity=ViolationSeverity.BLOCKING,
                        message=f"Chemical '{chemical}' is restricted in Zimbabwe",
                        field="action",
                        suggested_fix="Use approved alternative products",
                        can_override=False,
                        rule_id=f"compliance.zw.restricted.{chemical}"
                    ))
        
        return violations
    
    def check_safety_limits(
        self,
        recommendation: Dict[str, Any]
    ) -> List[SafetyViolation]:
        """Check recommendation against safety limits.
        
        Args:
            recommendation: Recommendation with potential dosage info
            
        Returns:
            List of safety limit violations
        """
        violations: List[SafetyViolation] = []
        
        # Check dosage if specified
        dose = recommendation.get("dose", recommendation.get("dosage"))
        action_text = self._get_action_text(recommendation).lower()
        
        if dose:
            dose_violations = self._check_dosage(dose, action_text)
            violations.extend(dose_violations)
        
        # Check for dangerous combinations
        dangerous_combos = [
            (["sulfur", "oil"], "Do not combine sulfur with oil-based products"),
            (["copper", "lime"], "Excessive copper with lime can cause phytotoxicity"),
        ]
        
        for combo_terms, warning in dangerous_combos:
            if all(term in action_text for term in combo_terms):
                violations.append(SafetyViolation(
                    violation_type="dangerous_combination",
                    severity=ViolationSeverity.WARNING,
                    message=warning,
                    field="action",
                    suggested_fix="Apply products separately or verify compatibility",
                    can_override=True,
                    rule_id="safety.combination"
                ))
        
        # Check for missing PPE warnings
        hazardous_keywords = ["pesticide", "herbicide", "fungicide", "insecticide", "spray"]
        if any(kw in action_text for kw in hazardous_keywords):
            warnings = recommendation.get("warnings", [])
            if not warnings or not any("protective" in str(w).lower() or "ppe" in str(w).lower() for w in warnings):
                violations.append(SafetyViolation(
                    violation_type="missing_ppe_warning",
                    severity=ViolationSeverity.INFO,
                    message="Chemical application should include PPE (Personal Protective Equipment) warnings",
                    field="warnings",
                    suggested_fix="Add warning about wearing protective gloves, mask, and eyewear",
                    can_override=True,
                    rule_id="safety.ppe.missing"
                ))
        
        return violations
    
    def check_inventory(
        self,
        recommendation: Dict[str, Any],
        inventory: Dict[str, Any]
    ) -> List[SafetyViolation]:
        """Check if required items are available in inventory.
        
        Args:
            recommendation: Recommendation with required items
            inventory: Available inventory
            
        Returns:
            List of inventory-related violations
        """
        violations: List[SafetyViolation] = []
        
        required = recommendation.get("required_items", recommendation.get("inputs", []))
        
        if not required:
            return violations
        
        available = inventory.get("available", inventory.get("stock", {}))
        
        for item in required:
            if isinstance(item, str):
                item_name = item
                item_qty = 1
            elif isinstance(item, dict):
                item_name = item.get("name", item.get("item", ""))
                item_qty = item.get("quantity", item.get("qty", 1))
            else:
                continue
            
            if item_name and item_name.lower() not in str(available).lower():
                violations.append(SafetyViolation(
                    violation_type="inventory_unavailable",
                    severity=ViolationSeverity.WARNING,
                    message=f"Required item '{item_name}' may not be in inventory",
                    field="required_items",
                    suggested_fix="Verify availability or source from nearby supplier",
                    can_override=True,
                    rule_id="inventory.availability"
                ))
        
        return violations
    
    def check_timing(
        self,
        recommendation: Dict[str, Any],
        crop_info: Dict[str, Any]
    ) -> List[SafetyViolation]:
        """Check timing constraints for recommendations.
        
        Args:
            recommendation: Recommendation with timing info
            crop_info: Crop growth stage and harvest info
            
        Returns:
            List of timing-related violations
        """
        violations: List[SafetyViolation] = []
        
        action_text = self._get_action_text(recommendation).lower()
        growth_stage = crop_info.get("growth_stage", "").lower()
        days_to_harvest = crop_info.get("days_to_harvest")
        
        # Check pre-harvest intervals
        if days_to_harvest is not None:
            for action_type, constraints in self._timing_constraints.items():
                if action_type in action_text:
                    phi = constraints["pre_harvest_days"]
                    if days_to_harvest < phi:
                        violations.append(SafetyViolation(
                            violation_type="pre_harvest_interval",
                            severity=ViolationSeverity.BLOCKING,
                            message=f"Cannot apply {action_type} within {phi} days of harvest "
                                    f"(harvest in {days_to_harvest} days)",
                            field="timing",
                            suggested_fix="Wait until after harvest or use alternative method",
                            can_override=False,
                            rule_id=f"timing.phi.{action_type}"
                        ))
        
        # Check growth stage appropriateness
        if "seedling" in growth_stage and "heavy fertilizer" in action_text:
            violations.append(SafetyViolation(
                violation_type="growth_stage_mismatch",
                severity=ViolationSeverity.WARNING,
                message="Heavy fertilizer application not recommended for seedling stage",
                field="timing",
                suggested_fix="Wait until plant is established or reduce dosage",
                can_override=True,
                rule_id="timing.stage.seedling"
            ))
        
        return violations
    
    def _get_action_text(self, recommendation: Dict[str, Any]) -> str:
        """Extract action text from recommendation.
        
        Args:
            recommendation: Recommendation dictionary
            
        Returns:
            Concatenated action text
        """
        parts = []
        
        for key in ["action", "actions", "recommendation", "description", "text"]:
            if key in recommendation:
                value = recommendation[key]
                if isinstance(value, str):
                    parts.append(value)
                elif isinstance(value, list):
                    parts.extend(str(v) for v in value)
        
        return " ".join(parts)
    
    def _check_dosage(
        self,
        dose: Any,
        action_text: str
    ) -> List[SafetyViolation]:
        """Check dosage against safety limits.
        
        Args:
            dose: Dosage specification
            action_text: Action text to identify product
            
        Returns:
            List of dosage violations
        """
        violations: List[SafetyViolation] = []
        
        # Parse dosage if string
        if isinstance(dose, str):
            try:
                # Extract numeric value
                import re
                match = re.search(r"(\d+\.?\d*)", dose)
                if match:
                    dose_value = float(match.group(1))
                else:
                    return violations
            except (ValueError, AttributeError):
                return violations
        elif isinstance(dose, (int, float)):
            dose_value = float(dose)
        else:
            return violations
        
        # Check against known limits
        for chemical, limits in self._dosage_limits.items():
            if chemical in action_text:
                if dose_value > limits["max"]:
                    violations.append(SafetyViolation(
                        violation_type="dosage_exceeded",
                        severity=ViolationSeverity.BLOCKING,
                        message=f"Dosage {dose_value} exceeds maximum safe limit "
                                f"{limits['max']} {limits['unit']} for {chemical}",
                        field="dose",
                        suggested_fix=f"Reduce dosage to maximum {limits['max']} {limits['unit']}",
                        can_override=False,
                        rule_id=f"dosage.max.{chemical}"
                    ))
                elif dose_value < limits["min"]:
                    violations.append(SafetyViolation(
                        violation_type="dosage_ineffective",
                        severity=ViolationSeverity.INFO,
                        message=f"Dosage {dose_value} may be below effective minimum "
                                f"{limits['min']} {limits['unit']} for {chemical}",
                        field="dose",
                        suggested_fix=f"Consider increasing to minimum {limits['min']} {limits['unit']}",
                        can_override=True,
                        rule_id=f"dosage.min.{chemical}"
                    ))
        
        return violations
