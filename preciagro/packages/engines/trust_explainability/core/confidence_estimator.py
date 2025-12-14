"""Confidence & Uncertainty Estimation Module.

Provides calibrated confidence scoring with epistemic/aleatoric
uncertainty quantification and ensemble disagreement handling.
"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple

from ..contracts.v1.schemas import ConfidenceMetrics
from ..contracts.v1.enums import UncertaintyType
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class ConfidenceEstimator:
    """Calibrated confidence scoring with uncertainty quantification.
    
    Distinguishes between:
    - Epistemic uncertainty (reducible): lack of knowledge/data
    - Aleatoric uncertainty (irreducible): inherent randomness
    """
    
    def __init__(self) -> None:
        """Initialize confidence estimator."""
        self.settings = get_settings()
    
    def estimate(
        self,
        model_outputs: List[Dict[str, Any]],
        evidence_confidences: Optional[List[float]] = None
    ) -> ConfidenceMetrics:
        """Estimate calibrated confidence from model outputs.
        
        Args:
            model_outputs: List of model output dictionaries with confidence scores
            evidence_confidences: Optional list of evidence quality confidences
            
        Returns:
            ConfidenceMetrics with full uncertainty breakdown
        """
        if not model_outputs:
            return self._create_low_confidence_metrics("No model outputs provided")
        
        # Extract confidences from outputs
        raw_confidences = self._extract_confidences(model_outputs)
        
        if not raw_confidences:
            return self._create_low_confidence_metrics("No confidence scores found")
        
        # Calculate ensemble statistics
        mean_conf = sum(raw_confidences) / len(raw_confidences)
        
        # Estimate epistemic uncertainty from ensemble disagreement
        epistemic = self._estimate_epistemic_uncertainty(raw_confidences)
        
        # Estimate aleatoric uncertainty from prediction softness
        aleatoric = self._estimate_aleatoric_uncertainty(model_outputs)
        
        # Adjust for evidence quality
        if evidence_confidences:
            evidence_factor = sum(evidence_confidences) / len(evidence_confidences)
            mean_conf *= evidence_factor
        
        # Apply calibration
        calibrated_conf = self._calibrate_confidence(mean_conf)
        
        # Classify uncertainty type
        uncertainty_type = self._classify_uncertainty(epistemic, aleatoric)
        
        # Compute component confidences
        component_confidences = {
            f"model_{i}": conf for i, conf in enumerate(raw_confidences)
        }
        
        return ConfidenceMetrics(
            overall_confidence=calibrated_conf,
            uncertainty_type=uncertainty_type,
            epistemic_uncertainty=epistemic,
            aleatoric_uncertainty=aleatoric,
            ensemble_agreement=1.0 - epistemic if len(raw_confidences) > 1 else None,
            num_ensemble_members=len(raw_confidences) if len(raw_confidences) > 1 else None,
            component_confidences=component_confidences,
            calibration_method="isotonic",
            meets_high_threshold=calibrated_conf >= self.settings.confidence_threshold_high,
            meets_action_threshold=calibrated_conf >= self.settings.confidence_threshold_action
        )
    
    def classify_uncertainty(self, metrics: ConfidenceMetrics) -> UncertaintyType:
        """Classify the type of uncertainty in the metrics.
        
        Args:
            metrics: Confidence metrics to classify
            
        Returns:
            UncertaintyType enum value
        """
        return metrics.uncertainty_type
    
    def check_threshold(
        self,
        confidence: float,
        action_type: str = "recommendation"
    ) -> Tuple[bool, str]:
        """Check if confidence meets threshold for action type.
        
        Args:
            confidence: Confidence score to check
            action_type: Type of action (recommendation, diagnosis, alert)
            
        Returns:
            Tuple of (passes_threshold, message)
        """
        # Different thresholds for different action types
        thresholds = {
            "recommendation": self.settings.confidence_threshold_action,
            "diagnosis": self.settings.confidence_threshold_medium,
            "alert": self.settings.confidence_threshold_high,
            "treatment": self.settings.confidence_threshold_high,
        }
        
        threshold = thresholds.get(action_type, self.settings.confidence_threshold_action)
        passes = confidence >= threshold
        
        if passes:
            if confidence >= self.settings.confidence_threshold_high:
                level = "high"
            elif confidence >= self.settings.confidence_threshold_medium:
                level = "medium"
            else:
                level = "low"
            message = f"Confidence {confidence:.2f} is {level} (threshold: {threshold:.2f})"
        else:
            message = f"Confidence {confidence:.2f} below threshold {threshold:.2f} for {action_type}"
        
        return passes, message
    
    def get_confidence_level(self, confidence: float) -> str:
        """Get human-readable confidence level.
        
        Args:
            confidence: Confidence score
            
        Returns:
            "high", "medium", or "low"
        """
        if confidence >= self.settings.confidence_threshold_high:
            return "high"
        elif confidence >= self.settings.confidence_threshold_medium:
            return "medium"
        else:
            return "low"
    
    def _extract_confidences(
        self,
        model_outputs: List[Dict[str, Any]]
    ) -> List[float]:
        """Extract confidence scores from model outputs.
        
        Args:
            model_outputs: List of model output dictionaries
            
        Returns:
            List of confidence scores
        """
        confidences = []
        
        for output in model_outputs:
            # Try common confidence field names
            for key in ["confidence", "score", "probability", "prob", "conf"]:
                if key in output:
                    try:
                        conf = float(output[key])
                        if 0.0 <= conf <= 1.0:
                            confidences.append(conf)
                            break
                    except (ValueError, TypeError):
                        continue
            
            # Check nested structures
            if "prediction" in output and isinstance(output["prediction"], dict):
                nested = output["prediction"]
                for key in ["confidence", "score"]:
                    if key in nested:
                        try:
                            conf = float(nested[key])
                            if 0.0 <= conf <= 1.0:
                                confidences.append(conf)
                                break
                        except (ValueError, TypeError):
                            continue
        
        return confidences
    
    def _estimate_epistemic_uncertainty(
        self,
        confidences: List[float]
    ) -> float:
        """Estimate epistemic uncertainty from ensemble variance.
        
        Higher variance indicates more epistemic uncertainty (model disagreement).
        
        Args:
            confidences: List of confidence scores
            
        Returns:
            Epistemic uncertainty score (0-1)
        """
        if len(confidences) < 2:
            # Single model - moderate epistemic uncertainty assumed
            return 0.3
        
        # Calculate variance
        mean = sum(confidences) / len(confidences)
        variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)
        
        # Map variance to 0-1 scale (max variance is 0.25 for 0-1 range)
        # Higher variance = higher epistemic uncertainty
        epistemic = min(variance * 4, 1.0)
        
        return epistemic
    
    def _estimate_aleatoric_uncertainty(
        self,
        model_outputs: List[Dict[str, Any]]
    ) -> float:
        """Estimate aleatoric uncertainty from prediction softness.
        
        Looks for probability distributions or multiple class scores.
        Flat distributions indicate high aleatoric uncertainty.
        
        Args:
            model_outputs: Model outputs with potential class distributions
            
        Returns:
            Aleatoric uncertainty score (0-1)
        """
        aleatoric_samples = []
        
        for output in model_outputs:
            # Look for class probabilities
            probs = None
            for key in ["probabilities", "class_scores", "scores", "logits"]:
                if key in output:
                    probs = output[key]
                    break
            
            if probs and isinstance(probs, (list, dict)):
                if isinstance(probs, dict):
                    probs = list(probs.values())
                
                if len(probs) > 1:
                    # Calculate entropy-based uncertainty
                    # Normalize to probabilities
                    total = sum(max(p, 1e-10) for p in probs)
                    normalized = [max(p, 1e-10) / total for p in probs]
                    
                    # Shannon entropy
                    entropy = -sum(p * math.log2(p) for p in normalized)
                    max_entropy = math.log2(len(normalized))
                    
                    # Normalized entropy as aleatoric uncertainty
                    if max_entropy > 0:
                        aleatoric_samples.append(entropy / max_entropy)
        
        if aleatoric_samples:
            return sum(aleatoric_samples) / len(aleatoric_samples)
        
        # Default moderate aleatoric uncertainty
        return 0.2
    
    def _classify_uncertainty(
        self,
        epistemic: float,
        aleatoric: float
    ) -> UncertaintyType:
        """Classify primary uncertainty type.
        
        Args:
            epistemic: Epistemic uncertainty score
            aleatoric: Aleatoric uncertainty score
            
        Returns:
            Dominant uncertainty type
        """
        if epistemic > 0.5 and aleatoric > 0.5:
            return UncertaintyType.MIXED
        elif epistemic > aleatoric:
            return UncertaintyType.EPISTEMIC
        else:
            return UncertaintyType.ALEATORIC
    
    def _calibrate_confidence(self, raw_confidence: float) -> float:
        """Apply calibration to raw confidence score.
        
        Uses a simple isotonic-style calibration adjustment.
        In production, this would use a learned calibration model.
        
        Args:
            raw_confidence: Raw confidence score
            
        Returns:
            Calibrated confidence score
        """
        # Simple sigmoid-based calibration
        # This adjusts overconfident predictions downward
        # In production: use temperature scaling or Platt calibration
        
        if raw_confidence >= 0.95:
            # High confidence models are often overconfident
            return raw_confidence * 0.95
        elif raw_confidence <= 0.2:
            # Very low confidence is usually accurate
            return raw_confidence
        else:
            # Moderate confidence - slight adjustment toward mean
            return 0.3 + (raw_confidence - 0.3) * 0.9
    
    def _create_low_confidence_metrics(self, reason: str) -> ConfidenceMetrics:
        """Create low-confidence metrics with explanation.
        
        Args:
            reason: Reason for low confidence
            
        Returns:
            Low confidence ConfidenceMetrics
        """
        logger.warning(f"Low confidence: {reason}")
        
        return ConfidenceMetrics(
            overall_confidence=0.0,
            uncertainty_type=UncertaintyType.EPISTEMIC,
            epistemic_uncertainty=1.0,
            aleatoric_uncertainty=0.0,
            meets_high_threshold=False,
            meets_action_threshold=False,
            component_confidences={"reason": reason}
        )
