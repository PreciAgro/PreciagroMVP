"""Recommendation Synthesis Core - Converts diagnoses into action plans."""

import logging
from typing import List, Dict, Any

from ..models.domain import (
    Diagnosis,
    Recommendation,
    RecommendationPlan,
    ActionType,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class RecommendationSynthesisCore:
    """Converts diagnoses into multi-step strategies and action plans."""
    
    def __init__(self):
        """Initialize the recommendation synthesis core."""
        self._action_templates = self._build_action_templates()
    
    def synthesize(
        self,
        diagnosis: Diagnosis,
        context: Dict[str, Any]
    ) -> RecommendationPlan:
        """
        Synthesize recommendations from diagnosis.
        
        Args:
            diagnosis: Ranked diagnosis
            context: Contextual information
            
        Returns:
            Recommendation plan
        """
        recommendations = []
        
        if not diagnosis.primary_hypothesis:
            # No diagnosis, return monitoring recommendation
            return self._create_monitoring_plan(context)
        
        # Generate recommendations for primary hypothesis
        primary_recs = self._generate_hypothesis_recommendations(
            diagnosis.primary_hypothesis, context
        )
        recommendations.extend(primary_recs)
        
        # Generate recommendations for secondary hypotheses if high confidence
        for hypothesis in diagnosis.hypotheses[1:3]:  # Top 2-3
            if hypothesis.belief_score >= 0.5:
                secondary_recs = self._generate_hypothesis_recommendations(
                    hypothesis, context, is_secondary=True
                )
                recommendations.extend(secondary_recs)
        
        # Determine execution order
        execution_order = self._determine_execution_order(recommendations)
        
        # Calculate total cost
        total_cost = self._calculate_total_cost(recommendations, context)
        
        # Create plan
        plan = RecommendationPlan(
            recommendations=recommendations,
            execution_order=execution_order,
            total_estimated_cost=total_cost,
            estimated_duration=self._estimate_duration(recommendations),
            success_criteria=self._define_success_criteria(diagnosis),
        )
        
        logger.info(
            f"Synthesized recommendation plan with {len(recommendations)} recommendations"
        )
        
        return plan
    
    def _generate_hypothesis_recommendations(
        self,
        hypothesis,
        context: Dict[str, Any],
        is_secondary: bool = False
    ) -> List[Recommendation]:
        """Generate recommendations for a hypothesis."""
        recommendations = []
        
        if hypothesis.category.value == "disease":
            recommendations.extend(self._generate_disease_recommendations(hypothesis, context))
        elif hypothesis.category.value == "pest":
            recommendations.extend(self._generate_pest_recommendations(hypothesis, context))
        elif hypothesis.category.value == "nutrient_deficiency":
            recommendations.extend(self._generate_nutrient_recommendations(hypothesis, context))
        elif hypothesis.category.value == "water_stress":
            recommendations.extend(self._generate_water_stress_recommendations(hypothesis, context))
        elif hypothesis.category.value == "environmental_stress":
            recommendations.extend(self._generate_environmental_stress_recommendations(hypothesis, context))
        elif hypothesis.category.value == "management_error":
            recommendations.extend(self._generate_management_error_recommendations(hypothesis, context))
        
        # Adjust priority for secondary hypotheses
        if is_secondary:
            for rec in recommendations:
                if rec.priority == "high":
                    rec.priority = "medium"
        
        return recommendations
    
    def _generate_disease_recommendations(
        self,
        hypothesis,
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate disease treatment recommendations."""
        recommendations = []
        
        disease_name = hypothesis.name
        crop_type = context.get("crop_type", "crop")
        
        # Treatment recommendation
        treatment_rec = Recommendation(
            type=ActionType.TREATMENT,
            title=f"Treat {disease_name}",
            description=f"Apply appropriate fungicide or treatment for {disease_name} on {crop_type}",
            steps=[
                f"Identify affected areas in the field",
                f"Prepare recommended fungicide according to label instructions",
                f"Apply treatment during optimal weather conditions (low wind, no rain expected)",
                f"Monitor field for 7-14 days to assess treatment effectiveness",
            ],
            timing="Apply as soon as possible, preferably in early morning or late evening",
            dosage={
                "fungicide": "Follow product label recommendations",
                "application_rate": "As per regional guidelines",
            },
            priority="high" if hypothesis.severity in ["high", "critical"] else "medium",
            impact_score=0.8,
            cost_estimate={
                "currency": "USD",
                "range": "50-200 per hectare",
            },
            supporting_hypothesis_ids=[hypothesis.id],
            evidence_ids=hypothesis.evidence_ids,
            confidence=hypothesis.belief_score,
            warnings=[
                "Wear protective equipment during application",
                "Follow pre-harvest interval (PHI) requirements",
                "Check weather forecast before application",
            ],
        )
        recommendations.append(treatment_rec)
        
        # Prevention recommendation
        prevention_rec = Recommendation(
            type=ActionType.PREVENTION,
            title=f"Prevent {disease_name} Spread",
            description=f"Implement cultural practices to prevent {disease_name} from spreading",
            steps=[
                "Remove and destroy severely affected plants",
                "Improve field drainage if waterlogging is present",
                "Maintain proper plant spacing for air circulation",
                "Avoid overhead irrigation during disease-prone periods",
            ],
            priority="medium",
            impact_score=0.6,
            supporting_hypothesis_ids=[hypothesis.id],
            confidence=hypothesis.belief_score,
        )
        recommendations.append(prevention_rec)
        
        return recommendations
    
    def _generate_pest_recommendations(
        self,
        hypothesis,
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate pest control recommendations."""
        recommendations = []
        
        pest_name = hypothesis.name
        crop_type = context.get("crop_type", "crop")
        
        # Treatment recommendation
        treatment_rec = Recommendation(
            type=ActionType.TREATMENT,
            title=f"Control {pest_name}",
            description=f"Apply appropriate pesticide or biological control for {pest_name} on {crop_type}",
            steps=[
                f"Confirm pest identification through field scouting",
                f"Select appropriate control method (chemical, biological, or integrated)",
                f"Apply treatment when pest population reaches economic threshold",
                f"Monitor pest population after treatment",
            ],
            timing="Apply during early pest stages for best effectiveness",
            dosage={
                "pesticide": "Follow product label and economic threshold guidelines",
            },
            priority="high" if hypothesis.severity in ["high", "critical"] else "medium",
            impact_score=0.75,
            cost_estimate={
                "currency": "USD",
                "range": "30-150 per hectare",
            },
            supporting_hypothesis_ids=[hypothesis.id],
            evidence_ids=hypothesis.evidence_ids,
            confidence=hypothesis.belief_score,
            warnings=[
                "Use integrated pest management (IPM) principles",
                "Protect beneficial insects",
                "Follow safety guidelines for pesticide application",
            ],
        )
        recommendations.append(treatment_rec)
        
        return recommendations
    
    def _generate_nutrient_recommendations(
        self,
        hypothesis,
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate nutrient application recommendations."""
        recommendations = []
        
        deficiency_name = hypothesis.name
        crop_type = context.get("crop_type", "crop")
        
        # Nutrient application recommendation
        nutrient_rec = Recommendation(
            type=ActionType.NUTRIENT_APPLICATION,
            title=f"Address {deficiency_name}",
            description=f"Apply appropriate fertilizer to address {deficiency_name} in {crop_type}",
            steps=[
                f"Confirm nutrient deficiency through soil or tissue testing",
                f"Calculate required nutrient application rate based on crop needs",
                f"Select appropriate fertilizer formulation",
                f"Apply fertilizer at recommended timing for crop growth stage",
            ],
            timing="Apply during active growth phase for best uptake",
            dosage={
                "nutrient": deficiency_name.split()[0],  # Extract nutrient name
                "rate": "Based on soil test and crop requirements",
            },
            priority="medium",
            impact_score=0.7,
            cost_estimate={
                "currency": "USD",
                "range": "40-120 per hectare",
            },
            supporting_hypothesis_ids=[hypothesis.id],
            evidence_ids=hypothesis.evidence_ids,
            confidence=hypothesis.belief_score,
            warnings=[
                "Avoid over-application to prevent nutrient imbalances",
                "Consider split applications for better efficiency",
            ],
        )
        recommendations.append(nutrient_rec)
        
        return recommendations
    
    def _generate_water_stress_recommendations(
        self,
        hypothesis,
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate water management recommendations."""
        recommendations = []
        
        # Water management recommendation
        water_rec = Recommendation(
            type=ActionType.WATER_MANAGEMENT,
            title="Address Water Stress",
            description="Implement water management practices to address water stress",
            steps=[
                "Assess current soil moisture levels",
                "Increase irrigation frequency if irrigation is available",
                "Implement water conservation practices (mulching, reduced tillage)",
                "Monitor soil moisture regularly",
            ],
            timing="Implement immediately to prevent further stress",
            priority="high",
            impact_score=0.8,
            cost_estimate={
                "currency": "USD",
                "range": "20-100 per hectare",
            },
            supporting_hypothesis_ids=[hypothesis.id],
            evidence_ids=hypothesis.evidence_ids,
            confidence=hypothesis.belief_score,
        )
        recommendations.append(water_rec)
        
        return recommendations
    
    def _generate_environmental_stress_recommendations(
        self,
        hypothesis,
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate environmental stress management recommendations."""
        recommendations = []
        
        # Monitoring recommendation
        monitoring_rec = Recommendation(
            type=ActionType.MONITORING,
            title="Monitor Environmental Conditions",
            description="Monitor and manage environmental stress factors",
            steps=[
                "Track temperature and humidity patterns",
                "Implement protective measures if extreme weather is forecast",
                "Adjust planting or management timing if possible",
            ],
            priority="medium",
            impact_score=0.5,
            supporting_hypothesis_ids=[hypothesis.id],
            confidence=hypothesis.belief_score,
        )
        recommendations.append(monitoring_rec)
        
        return recommendations
    
    def _generate_management_error_recommendations(
        self,
        hypothesis,
        context: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate management practice correction recommendations."""
        recommendations = []
        
        # Cultural practice recommendation
        practice_rec = Recommendation(
            type=ActionType.CULTURAL_PRACTICE,
            title="Correct Management Practices",
            description="Adjust management practices to address identified issues",
            steps=[
                "Review current management practices",
                "Identify specific practices that need adjustment",
                "Implement corrected practices",
                "Monitor outcomes",
            ],
            priority="medium",
            impact_score=0.6,
            supporting_hypothesis_ids=[hypothesis.id],
            confidence=hypothesis.belief_score,
        )
        recommendations.append(practice_rec)
        
        return recommendations
    
    def _determine_execution_order(self, recommendations: List[Recommendation]) -> List[str]:
        """Determine recommended execution order."""
        # Sort by priority and urgency
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        
        sorted_recs = sorted(
            recommendations,
            key=lambda r: (priority_order.get(r.priority, 3), -r.impact_score)
        )
        
        return [rec.id for rec in sorted_recs]
    
    def _calculate_total_cost(
        self,
        recommendations: List[Recommendation],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate total estimated cost."""
        total_min = 0.0
        total_max = 0.0
        
        for rec in recommendations:
            if rec.cost_estimate:
                cost_range = rec.cost_estimate.get("range", "")
                # Simple parsing: "50-200" -> 50, 200
                if "-" in cost_range:
                    try:
                        parts = cost_range.split("-")
                        min_val = float(parts[0].strip())
                        max_val = float(parts[1].split()[0].strip())
                        total_min += min_val
                        total_max += max_val
                    except (ValueError, IndexError):
                        pass
        
        return {
            "currency": "USD",
            "min": total_min,
            "max": total_max,
            "range": f"{total_min:.0f}-{total_max:.0f} per hectare",
        }
    
    def _estimate_duration(self, recommendations: List[Recommendation]) -> str:
        """Estimate total duration to complete recommendations."""
        # Simple heuristic: 1-2 days per recommendation
        days = len(recommendations) * 1.5
        return f"{int(days)}-{int(days * 1.5)} days"
    
    def _define_success_criteria(self, diagnosis: Diagnosis) -> List[str]:
        """Define success criteria for the plan."""
        criteria = []
        
        if diagnosis.primary_hypothesis:
            criteria.append(
                f"Observe reduction in {diagnosis.primary_hypothesis.name} symptoms within 7-14 days"
            )
            criteria.append("Monitor crop health improvement")
        
        criteria.append("No new symptoms appear")
        criteria.append("Crop continues normal growth")
        
        return criteria
    
    def _create_monitoring_plan(self, context: Dict[str, Any]) -> RecommendationPlan:
        """Create monitoring plan when no clear diagnosis."""
        monitoring_rec = Recommendation(
            type=ActionType.MONITORING,
            title="Monitor Crop Health",
            description="Continue monitoring crop health and collect additional observations",
            steps=[
                "Regularly inspect field for new symptoms",
                "Take photos of affected areas",
                "Record environmental conditions",
                "Consider consulting agricultural extension service",
            ],
            priority="low",
            impact_score=0.3,
            confidence=0.5,
        )
        
        return RecommendationPlan(
            recommendations=[monitoring_rec],
            execution_order=[monitoring_rec.id],
            success_criteria=["Additional diagnostic information collected"],
        )
    
    def _build_action_templates(self) -> Dict[str, Any]:
        """Build action recommendation templates."""
        return {
            "treatment_priority": "high",
            "prevention_priority": "medium",
            "monitoring_priority": "low",
        }

