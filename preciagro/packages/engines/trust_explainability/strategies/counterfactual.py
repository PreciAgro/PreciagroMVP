"""Counterfactual Explanation Strategy.

Generates "what if" explanations showing minimal changes
needed to flip a prediction or increase confidence.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .base import BaseExplainer
from ..contracts.v1.schemas import EvidenceItem, ExplanationArtifact
from ..contracts.v1.enums import ExplanationLevel, ExplanationStrategy

logger = logging.getLogger(__name__)


@dataclass
class Counterfactual:
    """A single counterfactual explanation."""
    
    feature: str
    original_value: Any
    suggested_value: Any
    impact: float  # Change in confidence
    cost: float  # Cost of making this change (0-1)
    actionable: bool  # Whether farmer can act on this
    explanation: str  # Human-readable explanation


@dataclass
class CounterfactualSet:
    """Set of counterfactuals for a prediction."""
    
    original_prediction: str
    original_confidence: float
    target_prediction: Optional[str]
    counterfactuals: List[Counterfactual]
    combined_impact: float
    feasibility_score: float


class CounterfactualExplainer(BaseExplainer):
    """Generates counterfactual 'what if' explanations.
    
    Shows minimal feature changes needed to:
    - Flip a prediction to a desired outcome
    - Increase confidence above a threshold
    - Understand feature sensitivities
    """
    
    @property
    def strategy_type(self) -> ExplanationStrategy:
        return ExplanationStrategy.COUNTERFACTUAL
    
    def __init__(self) -> None:
        """Initialize counterfactual explainer."""
        # Feature actionability and cost database
        self._feature_costs: Dict[str, float] = {
            # Soil features - moderately actionable
            "pH": 0.3,  # Can be adjusted with lime/sulfur
            "nitrogen": 0.2,
            "phosphorus": 0.3,
            "potassium": 0.3,
            "organic_matter": 0.5,
            "moisture": 0.1,  # Irrigation
            
            # Environmental - mostly not actionable
            "temperature": 0.9,  # Can only use shade/timing
            "humidity": 0.8,
            "rainfall": 1.0,  # Cannot control
            
            # Management - highly actionable
            "planting_date": 0.1,
            "seed_variety": 0.2,
            "fertilizer_amount": 0.1,
            "irrigation_frequency": 0.1,
            "pesticide_application": 0.2,
        }
        
        # Feature value ranges for perturbation
        self._feature_ranges: Dict[str, Tuple[float, float]] = {
            "pH": (4.0, 9.0),
            "nitrogen": (0, 200),
            "phosphorus": (0, 100),
            "potassium": (0, 300),
            "moisture": (0, 100),
            "temperature": (0, 45),
            "humidity": (0, 100),
        }
        
        logger.info("CounterfactualExplainer initialized")
    
    def explain(
        self,
        evidence: List[EvidenceItem],
        model_output: Dict[str, Any],
        level: ExplanationLevel = ExplanationLevel.FARMER,
        language: str = "en"
    ) -> ExplanationArtifact:
        """Generate counterfactual explanation.
        
        Args:
            evidence: Evidence items with feature data
            model_output: Model output to explain
            level: Target audience level
            language: Output language
            
        Returns:
            ExplanationArtifact with counterfactuals
        """
        # Extract features from evidence and model output
        features = self._extract_features(evidence, model_output)
        
        # Get prediction info
        prediction = model_output.get(
            "diagnosis",
            model_output.get("prediction", "Unknown")
        )
        confidence = model_output.get("confidence", 0.0)
        
        # Generate counterfactuals
        cf_set = self.generate_counterfactuals(
            features=features,
            current_prediction=prediction,
            current_confidence=confidence,
            target_confidence=0.9,  # Aim for high confidence
            max_changes=3
        )
        
        # Format explanation based on level
        if level == ExplanationLevel.FARMER:
            content = self._format_farmer_counterfactuals(cf_set, language)
            content_type = "text"
        elif level == ExplanationLevel.EXPERT:
            content = self._format_expert_counterfactuals(cf_set)
            content_type = "text"
        else:
            content = self._format_auditor_counterfactuals(cf_set, features)
            content_type = "structured"
        
        return ExplanationArtifact(
            strategy=ExplanationStrategy.COUNTERFACTUAL,
            level=level,
            content_type=content_type,
            content=content,
            structured_data={
                "counterfactuals": [
                    {
                        "feature": cf.feature,
                        "original": cf.original_value,
                        "suggested": cf.suggested_value,
                        "impact": cf.impact,
                        "actionable": cf.actionable,
                    }
                    for cf in cf_set.counterfactuals
                ],
                "combined_impact": cf_set.combined_impact,
                "feasibility": cf_set.feasibility_score,
            },
            cited_evidence_ids=self.get_cited_evidence_ids(evidence),
            relevance_score=cf_set.feasibility_score
        )
    
    def supports(self, model_type: str) -> bool:
        """Check if this strategy supports the model type.
        
        Args:
            model_type: Type of model
            
        Returns:
            True for tabular/structured models
        """
        return model_type.lower() in [
            "tabular", "structured", "ml", "xgboost",
            "random_forest", "gradient_boosting"
        ]
    
    def generate_counterfactuals(
        self,
        features: Dict[str, Any],
        current_prediction: str,
        current_confidence: float,
        target_confidence: float = 0.9,
        target_prediction: Optional[str] = None,
        max_changes: int = 3
    ) -> CounterfactualSet:
        """Generate counterfactual explanations.
        
        Uses a simplified DiCE-style approach:
        1. Identify features with high sensitivity
        2. Propose minimal changes
        3. Rank by cost and actionability
        
        Args:
            features: Current feature values
            current_prediction: Current prediction
            current_confidence: Current confidence
            target_confidence: Desired confidence level
            target_prediction: Optional target prediction
            max_changes: Maximum number of changes
            
        Returns:
            CounterfactualSet with proposed changes
        """
        counterfactuals: List[Counterfactual] = []
        
        # Analyze each feature for potential counterfactuals
        for feature, value in features.items():
            if not isinstance(value, (int, float)):
                continue
            
            # Get feature cost (lower = more actionable)
            cost = self._feature_costs.get(feature.lower(), 0.5)
            actionable = cost < 0.7
            
            # Calculate potential perturbation
            cf = self._generate_single_counterfactual(
                feature=feature,
                current_value=value,
                current_confidence=current_confidence,
                target_confidence=target_confidence,
                cost=cost,
                actionable=actionable
            )
            
            if cf:
                counterfactuals.append(cf)
        
        # Sort by impact/cost ratio (best value first)
        counterfactuals.sort(
            key=lambda cf: (cf.actionable, cf.impact / max(cf.cost, 0.1)),
            reverse=True
        )
        
        # Take top N
        selected = counterfactuals[:max_changes]
        
        # Calculate combined impact
        combined_impact = sum(cf.impact for cf in selected)
        
        # Calculate feasibility (inverse of average cost)
        avg_cost = sum(cf.cost for cf in selected) / len(selected) if selected else 1.0
        feasibility = 1.0 - avg_cost
        
        return CounterfactualSet(
            original_prediction=current_prediction,
            original_confidence=current_confidence,
            target_prediction=target_prediction,
            counterfactuals=selected,
            combined_impact=min(combined_impact, 1.0 - current_confidence),
            feasibility_score=feasibility
        )
    
    def _generate_single_counterfactual(
        self,
        feature: str,
        current_value: float,
        current_confidence: float,
        target_confidence: float,
        cost: float,
        actionable: bool
    ) -> Optional[Counterfactual]:
        """Generate a single counterfactual for a feature.
        
        Args:
            feature: Feature name
            current_value: Current feature value
            current_confidence: Current model confidence
            target_confidence: Target confidence
            cost: Cost of changing this feature
            actionable: Whether farmer can act on this
            
        Returns:
            Counterfactual or None if not applicable
        """
        # Get valid range for this feature
        feature_key = feature.lower()
        value_range = self._feature_ranges.get(feature_key, (0, 100))
        min_val, max_val = value_range
        
        # Determine direction of change - heuristic based on feature type
        # In production, this would use model gradients
        if feature_key in ["pH"]:
            # For pH, optimal is around 6.5
            optimal = 6.5
            suggested = optimal
            direction = "toward optimal"
        elif feature_key in ["nitrogen", "phosphorus", "potassium"]:
            # For nutrients, assume deficiency is common
            suggested = min(current_value * 1.3, max_val)
            direction = "increase"
        elif feature_key in ["moisture"]:
            # Optimal moisture around 60-70%
            if current_value < 60:
                suggested = 65
                direction = "increase"
            elif current_value > 80:
                suggested = 70
                direction = "decrease"
            else:
                return None  # Already optimal
        else:
            # Generic: perturb by 20%
            suggested = current_value * 1.2
            direction = "adjust"
        
        # Clamp to valid range
        suggested = max(min_val, min(suggested, max_val))
        
        # Skip if change is minimal
        if abs(suggested - current_value) < 0.01 * max_val:
            return None
        
        # Estimate impact (simplified - in production use model)
        confidence_gap = target_confidence - current_confidence
        impact = min(confidence_gap * (1 - cost), 0.3)
        
        # Generate explanation
        explanation = self._format_change_explanation(
            feature, current_value, suggested, direction
        )
        
        return Counterfactual(
            feature=feature,
            original_value=round(current_value, 2),
            suggested_value=round(suggested, 2),
            impact=round(impact, 3),
            cost=cost,
            actionable=actionable,
            explanation=explanation
        )
    
    def _extract_features(
        self,
        evidence: List[EvidenceItem],
        model_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract features from evidence and model output.
        
        Args:
            evidence: Evidence items
            model_output: Model output
            
        Returns:
            Dictionary of feature values
        """
        features: Dict[str, Any] = {}
        
        # Extract from model output
        for key in ["features", "inputs", "data"]:
            if key in model_output and isinstance(model_output[key], dict):
                features.update(model_output[key])
        
        # Extract from evidence metadata
        for ev in evidence:
            if ev.metadata:
                for key in ["soil", "weather", "sensor_data", "features"]:
                    if key in ev.metadata and isinstance(ev.metadata[key], dict):
                        features.update(ev.metadata[key])
        
        return features
    
    def _format_change_explanation(
        self,
        feature: str,
        current: float,
        suggested: float,
        direction: str
    ) -> str:
        """Format a change as human-readable explanation.
        
        Args:
            feature: Feature name
            current: Current value
            suggested: Suggested value
            direction: Direction of change
            
        Returns:
            Human-readable explanation
        """
        # Format feature name
        readable_name = feature.replace("_", " ").title()
        
        # Calculate change
        change = suggested - current
        change_pct = abs(change / current * 100) if current != 0 else 100
        
        if direction == "toward optimal":
            return f"Adjust {readable_name} from {current:.1f} to {suggested:.1f} (optimal range)"
        elif direction == "increase":
            return f"Increase {readable_name} by {change_pct:.0f}% (from {current:.1f} to {suggested:.1f})"
        elif direction == "decrease":
            return f"Decrease {readable_name} by {change_pct:.0f}% (from {current:.1f} to {suggested:.1f})"
        else:
            return f"Adjust {readable_name} from {current:.1f} to {suggested:.1f}"
    
    def _format_farmer_counterfactuals(
        self,
        cf_set: CounterfactualSet,
        language: str
    ) -> str:
        """Format counterfactuals for farmer audience.
        
        Args:
            cf_set: Counterfactual set
            language: Output language
            
        Returns:
            Farmer-friendly explanation
        """
        if not cf_set.counterfactuals:
            return "The current conditions are close to optimal. No major changes recommended."
        
        # Filter to actionable only
        actionable = [cf for cf in cf_set.counterfactuals if cf.actionable]
        
        if not actionable:
            return (
                f"Confidence is {cf_set.original_confidence:.0%}. "
                "Higher confidence would require environmental changes beyond farmer control."
            )
        
        lines = [
            f"Current confidence: {cf_set.original_confidence:.0%}. "
            "To improve confidence, consider:"
        ]
        
        for i, cf in enumerate(actionable[:3], 1):
            lines.append(f"{i}. {cf.explanation}")
        
        potential = cf_set.original_confidence + cf_set.combined_impact
        lines.append(f"\nThese changes could improve confidence to ~{potential:.0%}.")
        
        return "\n".join(lines)
    
    def _format_expert_counterfactuals(
        self,
        cf_set: CounterfactualSet
    ) -> str:
        """Format counterfactuals for expert audience.
        
        Args:
            cf_set: Counterfactual set
            
        Returns:
            Expert-level explanation
        """
        lines = [
            f"**Counterfactual Analysis**",
            f"",
            f"**Original**: {cf_set.original_prediction} ({cf_set.original_confidence:.1%} confidence)",
            f"**Feasibility**: {cf_set.feasibility_score:.1%}",
            f"",
            "**Proposed Changes**:"
        ]
        
        for cf in cf_set.counterfactuals:
            actionable_tag = "✓" if cf.actionable else "✗"
            lines.append(
                f"- [{actionable_tag}] **{cf.feature}**: "
                f"{cf.original_value} → {cf.suggested_value} "
                f"(impact: +{cf.impact:.1%}, cost: {cf.cost:.1%})"
            )
        
        lines.extend([
            "",
            f"**Combined Impact**: +{cf_set.combined_impact:.1%} confidence",
            f"**Potential Result**: {cf_set.original_confidence + cf_set.combined_impact:.1%} confidence"
        ])
        
        return "\n".join(lines)
    
    def _format_auditor_counterfactuals(
        self,
        cf_set: CounterfactualSet,
        features: Dict[str, Any]
    ) -> str:
        """Format counterfactuals for auditor (JSON).
        
        Args:
            cf_set: Counterfactual set
            features: Original feature values
            
        Returns:
            JSON string for auditing
        """
        import json
        
        audit_data = {
            "original_features": features,
            "original_prediction": cf_set.original_prediction,
            "original_confidence": cf_set.original_confidence,
            "counterfactuals": [
                {
                    "feature": cf.feature,
                    "original_value": cf.original_value,
                    "suggested_value": cf.suggested_value,
                    "impact": cf.impact,
                    "cost": cf.cost,
                    "actionable": cf.actionable,
                    "explanation": cf.explanation
                }
                for cf in cf_set.counterfactuals
            ],
            "combined_impact": cf_set.combined_impact,
            "feasibility_score": cf_set.feasibility_score,
            "method": "simplified_dice"
        }
        
        return json.dumps(audit_data, indent=2, default=str)
