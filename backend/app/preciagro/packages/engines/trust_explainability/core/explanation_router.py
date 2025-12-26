"""Explanation Routing Module.

Routes explanation requests to appropriate strategies based on
model type, evidence types, and configuration.
"""

import logging
from typing import Dict, List, Optional, Type

from ..contracts.v1.enums import ExplanationStrategy, EvidenceType
from ..contracts.v1.schemas import EvidenceItem
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


# Strategy type alias
StrategyClass = Type["BaseExplainer"]  # Forward reference


class ExplanationRouter:
    """Routes explanation requests to appropriate strategies.

    Supports pluggable strategies for CV, tabular, rule-based, and LLM explanations.
    """

    # Model type to strategy mapping
    MODEL_TYPE_STRATEGIES: Dict[str, ExplanationStrategy] = {
        "cv": ExplanationStrategy.CV,
        "image": ExplanationStrategy.CV,
        "vision": ExplanationStrategy.CV,
        "tabular": ExplanationStrategy.TABULAR,
        "structured": ExplanationStrategy.TABULAR,
        "ml": ExplanationStrategy.TABULAR,
        "rule": ExplanationStrategy.RULE,
        "expert_system": ExplanationStrategy.RULE,
        "llm": ExplanationStrategy.LLM,
        "language_model": ExplanationStrategy.LLM,
        "hybrid": ExplanationStrategy.HYBRID,
    }

    # Evidence type hints for strategy selection
    EVIDENCE_HINTS: Dict[EvidenceType, ExplanationStrategy] = {
        EvidenceType.IMAGE: ExplanationStrategy.CV,
        EvidenceType.SENSOR: ExplanationStrategy.TABULAR,
        EvidenceType.TEXT: ExplanationStrategy.LLM,
        EvidenceType.MODEL_OUTPUT: ExplanationStrategy.HYBRID,
        EvidenceType.RULE: ExplanationStrategy.RULE,
    }

    def __init__(self) -> None:
        """Initialize explanation router."""
        self.settings = get_settings()
        self._strategy_registry: Dict[ExplanationStrategy, StrategyClass] = {}
        self._strategy_instances: Dict[ExplanationStrategy, "BaseExplainer"] = {}

    def route(
        self,
        evidence: List[EvidenceItem],
        model_type: str,
        prefer_strategy: Optional[ExplanationStrategy] = None,
    ) -> ExplanationStrategy:
        """Determine best explanation strategy for the request.

        Args:
            evidence: List of evidence items
            model_type: Type of model being explained
            prefer_strategy: Optional preferred strategy override

        Returns:
            Selected ExplanationStrategy
        """
        # If preferred strategy is specified and enabled, use it
        if prefer_strategy and self._is_strategy_enabled(prefer_strategy):
            return prefer_strategy

        # Primary: look up by model type
        model_type_lower = model_type.lower()
        if model_type_lower in self.MODEL_TYPE_STRATEGIES:
            strategy = self.MODEL_TYPE_STRATEGIES[model_type_lower]
            if self._is_strategy_enabled(strategy):
                logger.debug(f"Selected strategy {strategy} based on model type {model_type}")
                return strategy

        # Secondary: infer from evidence types
        strategy = self._infer_from_evidence(evidence)
        if strategy and self._is_strategy_enabled(strategy):
            logger.debug(f"Selected strategy {strategy} based on evidence")
            return strategy

        # Default fallback
        logger.debug("Using default LLM strategy")
        return ExplanationStrategy.LLM

    def get_strategies_for_hybrid(
        self, evidence: List[EvidenceItem], model_type: str
    ) -> List[ExplanationStrategy]:
        """Get list of strategies for hybrid explanation.

        Args:
            evidence: List of evidence items
            model_type: Type of model being explained

        Returns:
            List of applicable strategies
        """
        strategies: List[ExplanationStrategy] = []

        # Add primary strategy
        primary = self.route(evidence, model_type)
        if primary != ExplanationStrategy.HYBRID:
            strategies.append(primary)

        # Check for evidence that suggests additional strategies
        evidence_types = {ev.evidence_type for ev in evidence}

        if EvidenceType.IMAGE in evidence_types and self.settings.enable_gradcam:
            if ExplanationStrategy.CV not in strategies:
                strategies.append(ExplanationStrategy.CV)

        if any(et in evidence_types for et in [EvidenceType.SENSOR, EvidenceType.WEATHER]):
            if self.settings.enable_shap and ExplanationStrategy.TABULAR not in strategies:
                strategies.append(ExplanationStrategy.TABULAR)

        # Always include LLM for summary if enabled
        if self.settings.enable_llm_summary and ExplanationStrategy.LLM not in strategies:
            strategies.append(ExplanationStrategy.LLM)

        return strategies

    def register_strategy(
        self, strategy_type: ExplanationStrategy, strategy_class: StrategyClass
    ) -> None:
        """Register a strategy implementation.

        Args:
            strategy_type: Strategy enum value
            strategy_class: Strategy class to instantiate
        """
        self._strategy_registry[strategy_type] = strategy_class
        logger.info(f"Registered strategy {strategy_type.value}: {strategy_class.__name__}")

    def get_strategy_instance(
        self, strategy_type: ExplanationStrategy
    ) -> Optional["BaseExplainer"]:
        """Get or create a strategy instance.

        Args:
            strategy_type: Strategy enum value

        Returns:
            Strategy instance or None if not registered
        """
        # Return cached instance if available
        if strategy_type in self._strategy_instances:
            return self._strategy_instances[strategy_type]

        # Create new instance if class is registered
        if strategy_type in self._strategy_registry:
            try:
                instance = self._strategy_registry[strategy_type]()
                self._strategy_instances[strategy_type] = instance
                return instance
            except Exception as e:
                logger.error(f"Failed to instantiate strategy {strategy_type}: {e}")
                return None

        logger.warning(f"No strategy registered for {strategy_type}")
        return None

    def _infer_from_evidence(self, evidence: List[EvidenceItem]) -> Optional[ExplanationStrategy]:
        """Infer best strategy from evidence types.

        Args:
            evidence: List of evidence items

        Returns:
            Inferred strategy or None
        """
        if not evidence:
            return None

        # Count evidence types
        type_counts: Dict[EvidenceType, int] = {}
        for ev in evidence:
            type_counts[ev.evidence_type] = type_counts.get(ev.evidence_type, 0) + 1

        # Find dominant evidence type
        if not type_counts:
            return None

        dominant_type = max(type_counts, key=lambda t: type_counts[t])
        return self.EVIDENCE_HINTS.get(dominant_type)

    def _is_strategy_enabled(self, strategy: ExplanationStrategy) -> bool:
        """Check if a strategy is enabled in settings.

        Args:
            strategy: Strategy to check

        Returns:
            True if strategy is enabled
        """
        if strategy == ExplanationStrategy.CV:
            return self.settings.enable_gradcam
        elif strategy == ExplanationStrategy.TABULAR:
            return self.settings.enable_shap
        elif strategy == ExplanationStrategy.LLM:
            return self.settings.enable_llm_summary
        elif strategy == ExplanationStrategy.COUNTERFACTUAL:
            return self.settings.feature_counterfactual
        elif strategy == ExplanationStrategy.EXAMPLE:
            return self.settings.feature_example_based
        else:
            return True  # RULE and others always enabled


# Forward reference resolution
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..strategies.base import BaseExplainer
