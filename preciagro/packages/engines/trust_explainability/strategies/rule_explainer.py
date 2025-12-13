"""Rule-Based Reasoning Explainer.

Traces rule activations and shows which rules contributed to decisions.
"""

import logging
from typing import List, Dict, Any, Optional

from .base import BaseExplainer
from ..contracts.v1.schemas import EvidenceItem, ExplanationArtifact
from ..contracts.v1.enums import ExplanationLevel, ExplanationStrategy, EvidenceType

logger = logging.getLogger(__name__)


class RuleExplainer(BaseExplainer):
    """Explainer for rule-based/expert system decisions.
    
    Traces which rules activated and why.
    """
    
    @property
    def strategy_type(self) -> ExplanationStrategy:
        return ExplanationStrategy.RULE
    
    def __init__(self) -> None:
        """Initialize rule explainer."""
        logger.info("RuleExplainer initialized")
    
    def explain(
        self,
        evidence: List[EvidenceItem],
        model_output: Dict[str, Any],
        level: ExplanationLevel = ExplanationLevel.FARMER,
        language: str = "en"
    ) -> ExplanationArtifact:
        """Generate explanation for rule-based decision.
        
        Args:
            evidence: Evidence items
            model_output: Output containing triggered rules
            level: Target audience level
            language: Output language
            
        Returns:
            ExplanationArtifact with rule trace
        """
        # Extract rule information
        triggered_rules = model_output.get(
            "triggered_rules",
            model_output.get("rules", model_output.get("activated_rules", []))
        )
        
        recommendation = model_output.get(
            "recommendation",
            model_output.get("action", model_output.get("conclusion", "No recommendation"))
        )
        
        confidence = model_output.get("confidence", 1.0)  # Rules are typically deterministic
        
        # Find rule evidence
        rule_evidence = [
            ev for ev in evidence
            if ev.evidence_type == EvidenceType.RULE
        ]
        
        # Generate explanation based on level
        if level == ExplanationLevel.FARMER:
            content = self._generate_farmer_explanation(
                recommendation, triggered_rules, language
            )
            content_type = "text"
        elif level == ExplanationLevel.EXPERT:
            content = self._generate_expert_explanation(
                recommendation, triggered_rules, evidence
            )
            content_type = "text"
        else:  # AUDITOR
            content = self._generate_auditor_explanation(model_output, triggered_rules)
            content_type = "structured"
        
        return ExplanationArtifact(
            strategy=ExplanationStrategy.RULE,
            level=level,
            content_type=content_type,
            content=content,
            structured_data={
                "recommendation": recommendation,
                "triggered_rules": triggered_rules,
                "rule_count": len(triggered_rules),
                "confidence": confidence
            },
            cited_evidence_ids=self.get_cited_evidence_ids(evidence),
            relevance_score=confidence
        )
    
    def supports(self, model_type: str) -> bool:
        """Check if this strategy supports the model type.
        
        Args:
            model_type: Type of model
            
        Returns:
            True for rule-based systems
        """
        return model_type.lower() in [
            "rule", "rules", "expert_system", "knowledge_base", 
            "decision_tree", "logic", "constraint"
        ]
    
    def trace_rules(
        self,
        model_output: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Trace all rules that contributed to decision.
        
        Args:
            model_output: Model output with rule information
            
        Returns:
            List of rule trace objects
        """
        triggered = model_output.get("triggered_rules", [])
        traces = []
        
        for rule in triggered:
            if isinstance(rule, dict):
                traces.append({
                    "rule_id": rule.get("id", "unknown"),
                    "rule_name": rule.get("name", rule.get("id", "Unknown rule")),
                    "conditions_met": rule.get("conditions", []),
                    "action": rule.get("action", rule.get("conclusion")),
                    "priority": rule.get("priority", 0),
                    "confidence": rule.get("confidence", 1.0)
                })
            elif isinstance(rule, str):
                traces.append({
                    "rule_id": rule,
                    "rule_name": rule,
                    "conditions_met": [],
                    "action": None,
                    "priority": 0,
                    "confidence": 1.0
                })
        
        return traces
    
    def _generate_farmer_explanation(
        self,
        recommendation: str,
        triggered_rules: List[Any],
        language: str
    ) -> str:
        """Generate farmer-level rule explanation.
        
        Args:
            recommendation: Final recommendation
            triggered_rules: List of triggered rules
            language: Output language
            
        Returns:
            Simple explanation string
        """
        # Extract rule reasons
        reasons = self._extract_rule_reasons(triggered_rules)
        
        if language == "en":
            if reasons:
                reasons_str = "; ".join(reasons[:3])  # Top 3 reasons
                return (
                    f"Recommendation: {recommendation}. "
                    f"This is based on: {reasons_str}."
                )
            else:
                return f"Recommendation: {recommendation}."
        elif language == "sn":  # Shona
            if reasons:
                reasons_str = "; ".join(reasons[:3])
                return (
                    f"Zano: {recommendation}. "
                    f"Izvi zvakabudiswa ne: {reasons_str}."
                )
            else:
                return f"Zano: {recommendation}."
        else:
            if reasons:
                reasons_str = "; ".join(reasons[:3])
                return f"{recommendation}. Based on: {reasons_str}."
            else:
                return recommendation
    
    def _generate_expert_explanation(
        self,
        recommendation: str,
        triggered_rules: List[Any],
        evidence: List[EvidenceItem]
    ) -> str:
        """Generate expert-level rule explanation.
        
        Args:
            recommendation: Final recommendation
            triggered_rules: List of triggered rules
            evidence: Supporting evidence
            
        Returns:
            Detailed explanation
        """
        parts = [
            f"**Recommendation**: {recommendation}",
            "",
            "**Rule Trace**:"
        ]
        
        for i, rule in enumerate(triggered_rules[:10], 1):  # Top 10 rules
            if isinstance(rule, dict):
                rule_id = rule.get("id", f"rule_{i}")
                rule_name = rule.get("name", rule_id)
                conditions = rule.get("conditions", [])
                action = rule.get("action", "N/A")
                priority = rule.get("priority", 0)
                
                parts.append(f"\n{i}. **{rule_name}** (Priority: {priority})")
                if conditions:
                    parts.append("   Conditions:")
                    for cond in conditions[:5]:
                        parts.append(f"   - {cond}")
                parts.append(f"   Action: {action}")
            else:
                parts.append(f"\n{i}. {rule}")
        
        # Add evidence summary
        if evidence:
            parts.extend([
                "",
                "**Supporting Evidence**:"
            ])
            for ev in evidence[:5]:
                parts.append(f"- {ev.summary} (from {ev.source_engine})")
        
        return "\n".join(parts)
    
    def _generate_auditor_explanation(
        self,
        model_output: Dict[str, Any],
        triggered_rules: List[Any]
    ) -> str:
        """Generate auditor-level explanation (JSON).
        
        Args:
            model_output: Full model output
            triggered_rules: List of triggered rules
            
        Returns:
            JSON string for auditing
        """
        import json
        
        audit_data = {
            "model_output": model_output,
            "triggered_rules": triggered_rules,
            "rule_trace": self.trace_rules(model_output),
            "explanation_method": "rule_trace",
        }
        
        return json.dumps(audit_data, indent=2, default=str)
    
    def _extract_rule_reasons(self, triggered_rules: List[Any]) -> List[str]:
        """Extract human-readable reasons from rules.
        
        Args:
            triggered_rules: List of triggered rules
            
        Returns:
            List of reason strings
        """
        reasons = []
        
        for rule in triggered_rules:
            if isinstance(rule, dict):
                # Try to get human-readable reason
                reason = rule.get("reason", rule.get("description"))
                if reason:
                    reasons.append(str(reason))
                elif "name" in rule:
                    reasons.append(rule["name"])
                elif "conditions" in rule:
                    # Summarize conditions
                    conds = rule["conditions"]
                    if isinstance(conds, list) and conds:
                        reasons.append(str(conds[0]))
            elif isinstance(rule, str):
                reasons.append(rule)
        
        return reasons
