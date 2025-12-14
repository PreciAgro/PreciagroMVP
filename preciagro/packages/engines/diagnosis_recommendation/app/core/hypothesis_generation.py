"""Hypothesis Generation Layer - Enumerates plausible explanations."""

import logging
from typing import List, Dict, Any

from ..models.domain import (
    EvidenceGraph,
    Hypothesis,
    HypothesisCategory,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class HypothesisGenerationLayer:
    """Enumerates all plausible explanations for observed symptoms."""
    
    def __init__(self):
        """Initialize the hypothesis generation layer."""
        self._hypothesis_templates = self._build_hypothesis_templates()
    
    def generate_hypotheses(
        self,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """
        Generate plausible hypotheses from evidence graph.
        
        Args:
            evidence_graph: Evidence graph with observations and evidence
            context: Contextual information
            
        Returns:
            List of plausible hypotheses
        """
        hypotheses = []
        
        # Extract key signals from observations
        signals = {obs.signal for obs in evidence_graph.observations}
        
        # Generate hypotheses for each category
        for category in HypothesisCategory:
            if category == HypothesisCategory.UNKNOWN:
                continue  # Skip unknown, will add if no other hypotheses
            
            category_hypotheses = self._generate_category_hypotheses(
                category, signals, evidence_graph, context
            )
            hypotheses.extend(category_hypotheses)
        
        # If no hypotheses generated, add unknown
        if not hypotheses:
            hypotheses.append(self._create_unknown_hypothesis(evidence_graph, context))
        
        # Limit hypotheses
        if len(hypotheses) > settings.MAX_HYPOTHESES:
            hypotheses = hypotheses[:settings.MAX_HYPOTHESES]
        
        logger.info(f"Generated {len(hypotheses)} hypotheses")
        return hypotheses
    
    def _generate_category_hypotheses(
        self,
        category: HypothesisCategory,
        signals: set,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate hypotheses for a specific category."""
        hypotheses = []
        
        if category == HypothesisCategory.DISEASE:
            hypotheses.extend(self._generate_disease_hypotheses(signals, evidence_graph, context))
        elif category == HypothesisCategory.PEST:
            hypotheses.extend(self._generate_pest_hypotheses(signals, evidence_graph, context))
        elif category == HypothesisCategory.NUTRIENT_DEFICIENCY:
            hypotheses.extend(self._generate_nutrient_hypotheses(signals, evidence_graph, context))
        elif category == HypothesisCategory.WATER_STRESS:
            hypotheses.extend(self._generate_water_stress_hypotheses(signals, evidence_graph, context))
        elif category == HypothesisCategory.ENVIRONMENTAL_STRESS:
            hypotheses.extend(self._generate_environmental_stress_hypotheses(signals, evidence_graph, context))
        elif category == HypothesisCategory.MANAGEMENT_ERROR:
            hypotheses.extend(self._generate_management_error_hypotheses(signals, evidence_graph, context))
        elif category == HypothesisCategory.NORMAL_VARIATION:
            hypotheses.extend(self._generate_normal_variation_hypotheses(signals, evidence_graph, context))
        
        return hypotheses
    
    def _generate_disease_hypotheses(
        self,
        signals: set,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate disease hypotheses."""
        hypotheses = []
        crop_type = context.get("crop_type", "unknown")
        
        # Disease patterns
        disease_patterns = {
            "leaf_spot": ["Late Blight", "Early Blight", "Leaf Spot Disease"],
            "yellowing": ["Fusarium Wilt", "Verticillium Wilt", "Yellow Leaf Disease"],
            "blight": ["Late Blight", "Early Blight"],
            "rust": ["Rust Disease"],
            "mildew": ["Powdery Mildew", "Downy Mildew"],
        }
        
        for signal in signals:
            if signal in disease_patterns:
                for disease_name in disease_patterns[signal]:
                    # Get supporting evidence
                    supporting_evidence = [
                        ev.id for ev in evidence_graph.evidence
                        if any(obs_id in ev.observation_ids for obs in evidence_graph.observations
                               if obs.signal == signal)
                    ]
                    
                    hypothesis = Hypothesis(
                        category=HypothesisCategory.DISEASE,
                        name=disease_name,
                        description=f"{disease_name} affecting {crop_type} based on {signal} symptoms",
                        belief_score=0.5,  # Will be refined by reasoning core
                        prior_probability=0.2,
                        evidence_ids=supporting_evidence,
                        severity="medium",
                        urgency="medium",
                    )
                    hypotheses.append(hypothesis)
        
        return hypotheses
    
    def _generate_pest_hypotheses(
        self,
        signals: set,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate pest hypotheses."""
        hypotheses = []
        crop_type = context.get("crop_type", "unknown")
        
        # Pest patterns
        pest_patterns = {
            "leaf_damage": ["Aphids", "Caterpillars", "Leaf Miners"],
            "holes": ["Caterpillars", "Beetles"],
            "wilting": ["Root Knot Nematodes", "Stem Borers"],
        }
        
        for signal in signals:
            if signal in pest_patterns:
                for pest_name in pest_patterns[signal]:
                    supporting_evidence = [
                        ev.id for ev in evidence_graph.evidence
                        if any(obs_id in ev.observation_ids for obs in evidence_graph.observations
                               if obs.signal == signal)
                    ]
                    
                    hypothesis = Hypothesis(
                        category=HypothesisCategory.PEST,
                        name=pest_name,
                        description=f"{pest_name} infestation on {crop_type}",
                        belief_score=0.4,
                        prior_probability=0.15,
                        evidence_ids=supporting_evidence,
                        severity="medium",
                        urgency="medium",
                    )
                    hypotheses.append(hypothesis)
        
        return hypotheses
    
    def _generate_nutrient_hypotheses(
        self,
        signals: set,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate nutrient deficiency hypotheses."""
        hypotheses = []
        
        # Nutrient deficiency patterns
        nutrient_patterns = {
            "yellowing": ["Nitrogen Deficiency", "Iron Deficiency"],
            "purple_leaves": ["Phosphorus Deficiency"],
            "brown_edges": ["Potassium Deficiency"],
        }
        
        # Check for soil data observations
        soil_obs = [
            obs for obs in evidence_graph.observations
            if obs.signal.startswith("soil_")
        ]
        
        if soil_obs:
            for signal in signals:
                if signal in nutrient_patterns:
                    for deficiency_name in nutrient_patterns[signal]:
                        supporting_evidence = [
                            ev.id for ev in evidence_graph.evidence
                            if any(obs_id in ev.observation_ids for obs in evidence_graph.observations
                                   if obs.signal == signal or obs.signal.startswith("soil_"))
                        ]
                        
                        hypothesis = Hypothesis(
                            category=HypothesisCategory.NUTRIENT_DEFICIENCY,
                            name=deficiency_name,
                            description=f"{deficiency_name} based on symptoms and soil analysis",
                            belief_score=0.5,
                            prior_probability=0.2,
                            evidence_ids=supporting_evidence,
                            severity="low",
                            urgency="low",
                        )
                        hypotheses.append(hypothesis)
        
        return hypotheses
    
    def _generate_water_stress_hypotheses(
        self,
        signals: set,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate water stress hypotheses."""
        hypotheses = []
        
        # Check for water-related signals
        water_signals = {"wilting", "soil_moisture", "drought"}
        if any(s in signals for s in water_signals):
            supporting_evidence = [
                ev.id for ev in evidence_graph.evidence
                if any(obs_id in ev.observation_ids for obs in evidence_graph.observations
                       if obs.signal in water_signals)
            ]
            
            hypothesis = Hypothesis(
                category=HypothesisCategory.WATER_STRESS,
                name="Water Stress",
                description="Water stress due to insufficient irrigation or drought",
                belief_score=0.6,
                prior_probability=0.25,
                evidence_ids=supporting_evidence,
                severity="medium",
                urgency="high",
            )
            hypotheses.append(hypothesis)
        
        return hypotheses
    
    def _generate_environmental_stress_hypotheses(
        self,
        signals: set,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate environmental stress hypotheses."""
        hypotheses = []
        
        # Check for environmental signals
        env_signals = {"temperature", "humidity", "frost", "heat"}
        if any(s in signals for s in env_signals):
            supporting_evidence = [
                ev.id for ev in evidence_graph.evidence
                if any(obs_id in ev.observation_ids for obs in evidence_graph.observations
                       if obs.signal in env_signals)
            ]
            
            hypothesis = Hypothesis(
                category=HypothesisCategory.ENVIRONMENTAL_STRESS,
                name="Environmental Stress",
                description="Environmental stress from temperature, humidity, or weather extremes",
                belief_score=0.5,
                prior_probability=0.2,
                evidence_ids=supporting_evidence,
                severity="low",
                urgency="medium",
            )
            hypotheses.append(hypothesis)
        
        return hypotheses
    
    def _generate_management_error_hypotheses(
        self,
        signals: set,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate management error hypotheses."""
        hypotheses = []
        
        # Check for management-related signals
        mgmt_signals = {"over_fertilization", "over_watering", "timing_error"}
        if any(s in signals for s in mgmt_signals):
            supporting_evidence = [
                ev.id for ev in evidence_graph.evidence
                if any(obs_id in ev.observation_ids for obs in evidence_graph.observations
                       if obs.signal in mgmt_signals)
            ]
            
            hypothesis = Hypothesis(
                category=HypothesisCategory.MANAGEMENT_ERROR,
                name="Management Error",
                description="Symptoms consistent with management practice error",
                belief_score=0.4,
                prior_probability=0.15,
                evidence_ids=supporting_evidence,
                severity="medium",
                urgency="medium",
            )
            hypotheses.append(hypothesis)
        
        return hypotheses
    
    def _generate_normal_variation_hypotheses(
        self,
        signals: set,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate normal variation hypotheses."""
        hypotheses = []
        
        # If signals are mild and confidence is low, might be normal variation
        low_confidence_obs = [
            obs for obs in evidence_graph.observations
            if obs.confidence < 0.5
        ]
        
        if len(low_confidence_obs) > len(evidence_graph.observations) / 2:
            supporting_evidence = [
                ev.id for ev in evidence_graph.evidence
                if any(obs_id in ev.observation_ids for obs in low_confidence_obs)
            ]
            
            hypothesis = Hypothesis(
                category=HypothesisCategory.NORMAL_VARIATION,
                name="Normal Variation",
                description="Symptoms may be within normal crop variation",
                belief_score=0.3,
                prior_probability=0.1,
                evidence_ids=supporting_evidence,
                severity="low",
                urgency="low",
            )
            hypotheses.append(hypothesis)
        
        return hypotheses
    
    def _create_unknown_hypothesis(
        self,
        evidence_graph: EvidenceGraph,
        context: Dict[str, Any]
    ) -> Hypothesis:
        """Create unknown hypothesis when no other hypotheses match."""
        return Hypothesis(
            category=HypothesisCategory.UNKNOWN,
            name="Unknown Cause",
            description="Unable to determine cause from available observations",
            belief_score=0.1,
            prior_probability=0.05,
            evidence_ids=[ev.id for ev in evidence_graph.evidence],
            severity="low",
            urgency="low",
        )
    
    def _build_hypothesis_templates(self) -> Dict[str, Any]:
        """Build hypothesis generation templates."""
        return {
            "disease_prior": 0.2,
            "pest_prior": 0.15,
            "nutrient_prior": 0.2,
            "water_stress_prior": 0.25,
        }

