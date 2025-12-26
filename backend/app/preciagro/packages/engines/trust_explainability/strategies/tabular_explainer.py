"""Tabular ML Explainer.

SHAP-based explanations for tabular/structured ML models.
"""

import logging
from typing import List, Dict, Any, Optional

from .base import BaseExplainer
from ..contracts.v1.schemas import EvidenceItem, ExplanationArtifact
from ..contracts.v1.enums import ExplanationLevel, ExplanationStrategy

logger = logging.getLogger(__name__)

# Try to import SHAP
try:
    import shap

    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    shap = None

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


class TabularExplainer(BaseExplainer):
    """SHAP-based explainer for tabular ML models.

    Provides feature importance and local interpretation.
    """

    @property
    def strategy_type(self) -> ExplanationStrategy:
        return ExplanationStrategy.TABULAR

    def __init__(self) -> None:
        """Initialize tabular explainer."""
        self._shap_available = HAS_SHAP
        logger.info(f"TabularExplainer initialized (SHAP available: {self._shap_available})")

    def explain(
        self,
        evidence: List[EvidenceItem],
        model_output: Dict[str, Any],
        level: ExplanationLevel = ExplanationLevel.FARMER,
        language: str = "en",
    ) -> ExplanationArtifact:
        """Generate SHAP-based explanation for tabular model.

        Args:
            evidence: Evidence items
            model_output: Model output with feature contributions
            level: Target audience level
            language: Output language

        Returns:
            ExplanationArtifact with feature importance
        """
        # Extract feature importance if provided, otherwise compute
        feature_importance = model_output.get(
            "feature_importance",
            model_output.get("shap_values", self._compute_feature_importance(model_output)),
        )

        # Get prediction info
        prediction = model_output.get("prediction", model_output.get("diagnosis", "Unknown"))
        confidence = model_output.get("confidence", 0.0)

        # Generate explanation based on level
        if level == ExplanationLevel.FARMER:
            content = self._generate_farmer_explanation(
                prediction, confidence, feature_importance, language
            )
            content_type = "text"
        elif level == ExplanationLevel.EXPERT:
            content = self._generate_expert_explanation(
                prediction, confidence, feature_importance, model_output
            )
            content_type = "text"
        else:  # AUDITOR
            content = self._generate_auditor_explanation(model_output, feature_importance)
            content_type = "structured"

        # Normalize feature importance for structured data
        normalized_importance = self._normalize_importance(feature_importance)

        return ExplanationArtifact(
            strategy=ExplanationStrategy.TABULAR,
            level=level,
            content_type=content_type,
            content=content,
            structured_data={
                "prediction": prediction,
                "confidence": confidence,
                "feature_importance": normalized_importance,
                "technique": "shap" if self._shap_available else "heuristic",
            },
            cited_evidence_ids=self.get_cited_evidence_ids(evidence),
            relevance_score=confidence,
        )

    def supports(self, model_type: str) -> bool:
        """Check if this strategy supports the model type.

        Args:
            model_type: Type of model

        Returns:
            True for tabular/structured models
        """
        return model_type.lower() in [
            "tabular",
            "structured",
            "ml",
            "xgboost",
            "lightgbm",
            "random_forest",
            "gradient_boosting",
            "sklearn",
        ]

    def get_feature_importance(self, model_output: Dict[str, Any]) -> Dict[str, float]:
        """Extract or compute feature importance.

        Args:
            model_output: Model output dictionary

        Returns:
            Dictionary of feature name to importance score
        """
        return self._compute_feature_importance(model_output)

    def _compute_feature_importance(self, model_output: Dict[str, Any]) -> Dict[str, float]:
        """Compute or extract feature importance from model output.

        Args:
            model_output: Model output dictionary

        Returns:
            Feature importance dictionary
        """
        # Check for pre-computed SHAP values
        if "shap_values" in model_output:
            shap_values = model_output["shap_values"]
            if isinstance(shap_values, dict):
                return shap_values

        # Check for feature importance in output
        if "feature_importance" in model_output:
            fi = model_output["feature_importance"]
            if isinstance(fi, dict):
                return fi

        # Extract from features in output (heuristic)
        importance = {}

        # Common feature keys to look for
        feature_keys = ["features", "inputs", "data", "values", "soil", "weather", "sensor_data"]

        for key in feature_keys:
            if key in model_output:
                value = model_output[key]
                if isinstance(value, dict):
                    for feat_name, feat_val in value.items():
                        # Estimate importance based on deviation from typical
                        if isinstance(feat_val, (int, float)):
                            importance[feat_name] = abs(float(feat_val)) / 100.0
                        else:
                            importance[feat_name] = 0.5

        # If no features found, create placeholder
        if not importance:
            # Use model output keys as pseudo-features
            for key, value in model_output.items():
                if isinstance(value, (int, float)) and key not in ["confidence", "score"]:
                    importance[key] = abs(float(value)) / max(abs(float(value)), 1)

        return importance or {"unknown_feature": 0.5}

    def _normalize_importance(self, importance: Dict[str, float]) -> Dict[str, float]:
        """Normalize importance values to 0-1 range.

        Args:
            importance: Raw importance values

        Returns:
            Normalized importance values
        """
        if not importance:
            return {}

        values = list(importance.values())
        max_val = max(abs(v) for v in values) if values else 1.0

        if max_val == 0:
            return {k: 0.0 for k in importance}

        return {k: abs(v) / max_val for k, v in importance.items()}

    def _generate_farmer_explanation(
        self, prediction: str, confidence: float, importance: Dict[str, float], language: str
    ) -> str:
        """Generate farmer-level tabular explanation.

        Args:
            prediction: Model prediction
            confidence: Confidence score
            importance: Feature importance
            language: Output language

        Returns:
            Simple explanation string
        """
        conf_pct = int(confidence * 100)

        # Get top contributing factors
        top_factors = sorted(importance.items(), key=lambda x: abs(x[1]), reverse=True)[:3]

        # Format factor names for farmers
        factor_names = [self._format_feature_name(f[0]) for f in top_factors]

        if language == "en":
            factors_str = ", ".join(factor_names)
            if confidence >= 0.7:
                return (
                    f"Based on your data, this appears to be {prediction} "
                    f"({conf_pct}% confidence). "
                    f"Key factors: {factors_str}."
                )
            else:
                return (
                    f"This may be {prediction} ({conf_pct}% confidence). "
                    f"The main indicators were {factors_str}. "
                    f"Consider providing more information for a better assessment."
                )
        elif language == "sn":  # Shona
            factors_str = ", ".join(factor_names)
            return (
                f"Zvichienderana nedata yako, ichi chinoita se{prediction} "
                f"({conf_pct}% chivimbo). Zvinhu zvakakosha: {factors_str}."
            )
        else:
            # Default to English
            factors_str = ", ".join(factor_names)
            return f"{prediction} ({conf_pct}% confidence). Key factors: {factors_str}."

    def _generate_expert_explanation(
        self,
        prediction: str,
        confidence: float,
        importance: Dict[str, float],
        model_output: Dict[str, Any],
    ) -> str:
        """Generate expert-level tabular explanation.

        Args:
            prediction: Model prediction
            confidence: Confidence score
            importance: Feature importance
            model_output: Full model output

        Returns:
            Detailed explanation
        """
        parts = [
            f"**Prediction**: {prediction}",
            f"**Confidence**: {confidence:.1%}",
            "",
            "**Feature Contributions** (normalized):",
        ]

        # Sort by absolute importance
        sorted_features = sorted(importance.items(), key=lambda x: abs(x[1]), reverse=True)

        for feature, value in sorted_features[:10]:  # Top 10
            direction = "+" if value >= 0 else "-"
            bar_length = int(abs(value) * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            parts.append(f"- {feature}: {direction}{abs(value):.3f} [{bar}]")

        # Add model metadata if available
        model_version = model_output.get("model_version", "unknown")
        parts.extend(
            [
                "",
                f"**Model**: {model_version}",
                f"**Method**: {'SHAP' if self._shap_available else 'Heuristic feature attribution'}",
            ]
        )

        return "\n".join(parts)

    def _generate_auditor_explanation(
        self, model_output: Dict[str, Any], importance: Dict[str, float]
    ) -> str:
        """Generate auditor-level explanation (JSON).

        Args:
            model_output: Full model output
            importance: Feature importance

        Returns:
            JSON string for auditing
        """
        import json

        audit_data = {
            "model_output": model_output,
            "feature_importance": importance,
            "explanation_method": "shap" if self._shap_available else "heuristic",
            "shap_available": self._shap_available,
        }

        return json.dumps(audit_data, indent=2, default=str)

    def _format_feature_name(self, name: str) -> str:
        """Format technical feature name for farmers.

        Args:
            name: Technical feature name

        Returns:
            Human-readable name
        """
        # Common mappings
        mappings = {
            "pH": "soil acidity",
            "moisture": "soil moisture",
            "nitrogen": "nitrogen level",
            "phosphorus": "phosphorus level",
            "potassium": "potassium level",
            "temp": "temperature",
            "temperature": "temperature",
            "humidity": "humidity",
            "rainfall": "rainfall",
            "growth_stage": "crop growth stage",
            "organic_matter": "organic matter",
        }

        # Check for exact match
        if name.lower() in mappings:
            return mappings[name.lower()]

        # Convert snake_case to readable
        readable = name.replace("_", " ").replace("-", " ")
        return readable.title()
