"""Post-Structured-Output Safety Validator - Final safety pass after LLM formatting."""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..contracts.v1.schemas import AgroLLMResponse, RecommendedAction
from ..safety.constraint_engine import ConstraintViolation, ViolationSeverity

logger = logging.getLogger(__name__)


@dataclass
class SafetyPostProcessorConfig:
    """Configuration for post-processor safety checks."""
    
    banned_chemicals: List[str]
    illegal_dose_patterns: List[str]
    unsafe_timing_keywords: List[str]
    required_warnings_for_high_severity: bool = True
    validate_region_codes: bool = True
    valid_region_codes: Optional[List[str]] = None


class SafetyPostProcessor:
    """Final safety validator for structured LLM output."""
    
    def __init__(self, config: Optional[SafetyPostProcessorConfig] = None):
        """Initialize post-processor.
        
        Args:
            config: Post-processor configuration
        """
        self.config = config or SafetyPostProcessorConfig(
            banned_chemicals=[],
            illegal_dose_patterns=[],
            unsafe_timing_keywords=[],
            required_warnings_for_high_severity=True
        )
        logger.info("SafetyPostProcessor initialized")
    
    def validate_and_fix(
        self,
        response: AgroLLMResponse,
        request_context: Optional[Dict[str, Any]] = None
    ) -> tuple[AgroLLMResponse, List[ConstraintViolation]]:
        """Validate and fix structured output.
        
        Args:
            response: Structured LLM response
            request_context: Original request context
            
        Returns:
            Tuple of (fixed_response, violations)
        """
        violations = []
        fixed_response = response.model_copy(deep=True)
        
        # Validate and fix actions
        fixed_actions = []
        for action in fixed_response.diagnosis_card.recommended_actions:
            action_violations, fixed_action = self._validate_and_fix_action(
                action, request_context
            )
            violations.extend(action_violations)
            if fixed_action:
                fixed_actions.append(fixed_action)
        
        fixed_response.diagnosis_card.recommended_actions = fixed_actions
        
        # Check for illegal chemicals in all text
        violations.extend(self._check_illegal_chemicals(fixed_response))
        
        # Validate doses
        violations.extend(self._validate_doses(fixed_response))
        
        # Validate timing
        violations.extend(self._validate_timing(fixed_response, request_context))
        
        # Check for missing warnings
        violations.extend(self._check_missing_warnings(fixed_response))
        
        # Validate region codes if present
        if request_context:
            violations.extend(self._validate_region_codes(fixed_response, request_context))
        
        # Apply fixes based on violations
        for violation in violations:
            if violation.severity == ViolationSeverity.BLOCKING:
                # Remove or flag blocking violations
                logger.warning(f"Blocking violation detected: {violation.message}")
                fixed_response.flags.constraint_violation = True
                fixed_response.flags.needs_review = True
                fixed_response.diagnosis_card.warnings.append(
                    f"SAFETY ALERT: {violation.message}"
                )
            elif violation.severity == ViolationSeverity.WARNING:
                fixed_response.diagnosis_card.warnings.append(violation.message)
        
        return fixed_response, violations
    
    def _validate_and_fix_action(
        self,
        action: RecommendedAction,
        request_context: Optional[Dict[str, Any]]
    ) -> tuple[List[ConstraintViolation], Optional[RecommendedAction]]:
        """Validate and fix a single action."""
        violations = []
        fixed_action = action.model_copy(deep=True)
        
        # Check for banned chemicals
        action_text_lower = action.action.lower()
        for banned in self.config.banned_chemicals:
            if banned.lower() in action_text_lower:
                violations.append(ConstraintViolation(
                    type="banned_chemical_in_action",
                    severity=ViolationSeverity.BLOCKING,
                    message=f"Banned chemical '{banned}' found in action: {action.action}",
                    field="action",
                    suggested_fix=f"Remove or replace recommendation containing '{banned}'"
                ))
                # Remove the action if it contains banned chemical
                return violations, None
        
        # Validate dose format
        if action.dose:
            dose_violations = self._validate_dose_format(action.dose)
            violations.extend(dose_violations)
            if dose_violations:
                # Try to fix dose format
                fixed_dose = self._fix_dose_format(action.dose)
                if fixed_dose != action.dose:
                    fixed_action.dose = fixed_dose
                    logger.info(f"Fixed dose format: {action.dose} -> {fixed_dose}")
        
        return violations, fixed_action
    
    def _check_illegal_chemicals(
        self,
        response: AgroLLMResponse
    ) -> List[ConstraintViolation]:
        """Check for illegal chemicals in response text."""
        violations = []
        
        all_text = (
            response.generated_text + " " +
            " ".join(a.action for a in response.diagnosis_card.recommended_actions) + " " +
            " ".join(response.diagnosis_card.warnings)
        ).lower()
        
        for banned in self.config.banned_chemicals:
            if banned.lower() in all_text:
                violations.append(ConstraintViolation(
                    type="banned_chemical_detected",
                    severity=ViolationSeverity.BLOCKING,
                    message=f"Banned chemical '{banned}' detected in response",
                    field="response",
                    suggested_fix=f"Remove all references to '{banned}'"
                ))
        
        return violations
    
    def _validate_doses(
        self,
        response: AgroLLMResponse
    ) -> List[ConstraintViolation]:
        """Validate dose formats."""
        violations = []
        
        for action in response.diagnosis_card.recommended_actions:
            if action.dose:
                dose_violations = self._validate_dose_format(action.dose)
                violations.extend(dose_violations)
        
        return violations
    
    def _validate_dose_format(self, dose: str) -> List[ConstraintViolation]:
        """Validate dose format."""
        violations = []
        
        # Check for common illegal patterns
        for pattern in self.config.illegal_dose_patterns:
            if pattern.lower() in dose.lower():
                violations.append(ConstraintViolation(
                    type="illegal_dose_pattern",
                    severity=ViolationSeverity.WARNING,
                    message=f"Illegal dose pattern detected: {dose}",
                    field="dose",
                    suggested_fix="Use standard dose format (e.g., '2.5 kg/ha' or '500 ml/acre')"
                ))
        
        # Check for missing units
        if dose and not re.search(r'\d+\s*(kg|g|ml|l|ha|acre|%)', dose, re.IGNORECASE):
            violations.append(ConstraintViolation(
                type="missing_dose_units",
                severity=ViolationSeverity.WARNING,
                message=f"Dose missing units: {dose}",
                field="dose",
                suggested_fix="Add proper units (e.g., 'kg/ha', 'ml/acre')"
            ))
        
        return violations
    
    def _fix_dose_format(self, dose: str) -> str:
        """Attempt to fix dose format."""
        # Simple fix: ensure units are present
        if dose and not re.search(r'\d+\s*(kg|g|ml|l|ha|acre|%)', dose, re.IGNORECASE):
            # Try to infer units from context (basic heuristic)
            if any(keyword in dose.lower() for keyword in ['kg', 'kilogram']):
                return f"{dose} kg/ha"
            elif any(keyword in dose.lower() for keyword in ['ml', 'milliliter', 'liter']):
                return f"{dose} ml/acre"
        
        return dose
    
    def _validate_timing(
        self,
        response: AgroLLMResponse,
        request_context: Optional[Dict[str, Any]]
    ) -> List[ConstraintViolation]:
        """Validate timing recommendations."""
        violations = []
        
        for action in response.diagnosis_card.recommended_actions:
            if action.timing:
                timing_lower = action.timing.lower()
                
                # Check for unsafe timing keywords
                for keyword in self.config.unsafe_timing_keywords:
                    if keyword in timing_lower:
                        violations.append(ConstraintViolation(
                            type="unsafe_timing",
                            severity=ViolationSeverity.WARNING,
                            message=f"Potentially unsafe timing: {action.timing}",
                            field="timing",
                            suggested_fix="Review timing recommendation for safety"
                        ))
        
        return violations
    
    def _check_missing_warnings(
        self,
        response: AgroLLMResponse
    ) -> List[ConstraintViolation]:
        """Check for missing required warnings."""
        violations = []
        
        if self.config.required_warnings_for_high_severity:
            if response.diagnosis_card.severity == "high":
                # Check if warnings exist
                if not response.diagnosis_card.warnings:
                    violations.append(ConstraintViolation(
                        type="missing_warning_for_high_severity",
                        severity=ViolationSeverity.WARNING,
                        message="High severity diagnosis should include warnings",
                        field="warnings",
                        suggested_fix="Add appropriate safety warnings"
                    ))
                
                # Check if chemical actions have safety warnings
                chemical_keywords = ["pesticide", "herbicide", "fungicide", "chemical"]
                has_chemical_action = any(
                    any(keyword in action.action.lower() for keyword in chemical_keywords)
                    for action in response.diagnosis_card.recommended_actions
                )
                
                if has_chemical_action:
                    has_safety_warning = any(
                        "safety" in w.lower() or "protective" in w.lower() or "equipment" in w.lower()
                        for w in response.diagnosis_card.warnings
                    )
                    if not has_safety_warning:
                        violations.append(ConstraintViolation(
                            type="missing_safety_warning_for_chemicals",
                            severity=ViolationSeverity.WARNING,
                            message="Chemical application actions should include safety warnings",
                            field="warnings",
                            suggested_fix="Add safety warnings about protective equipment"
                        ))
        
        return violations
    
    def _validate_region_codes(
        self,
        response: AgroLLMResponse,
        request_context: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """Validate region codes in response."""
        violations = []
        
        if not self.config.validate_region_codes:
            return violations
        
        # Extract region code from request context
        request_region = request_context.get("geo", {}).get("region_code")
        
        if request_region and self.config.valid_region_codes:
            if request_region not in self.config.valid_region_codes:
                violations.append(ConstraintViolation(
                    type="invalid_region_code",
                    severity=ViolationSeverity.WARNING,
                    message=f"Unknown region code: {request_region}",
                    field="geo.region_code",
                    suggested_fix="Verify region code is valid"
                ))
        
        return violations






