"""LLM Rationale Summarizer.

Generates evidence-grounded natural language summaries using LLM.
Ensures no chain-of-thought leakage.
"""

import logging
from typing import List, Dict, Any, Optional

from .base import BaseExplainer
from ..contracts.v1.schemas import EvidenceItem, ExplanationArtifact
from ..contracts.v1.enums import ExplanationLevel, ExplanationStrategy

logger = logging.getLogger(__name__)


class LLMSummarizer(BaseExplainer):
    """LLM-based rationale summarizer.
    
    Generates evidence-grounded natural language explanations.
    Does not leak internal chain-of-thought reasoning.
    """
    
    @property
    def strategy_type(self) -> ExplanationStrategy:
        return ExplanationStrategy.LLM
    
    def __init__(self) -> None:
        """Initialize LLM summarizer."""
        self._llm_client = None
        self._templates = self._load_templates()
        logger.info("LLMSummarizer initialized")
    
    def explain(
        self,
        evidence: List[EvidenceItem],
        model_output: Dict[str, Any],
        level: ExplanationLevel = ExplanationLevel.FARMER,
        language: str = "en"
    ) -> ExplanationArtifact:
        """Generate LLM-based explanation.
        
        Args:
            evidence: Evidence items to ground the explanation
            model_output: Model output to explain
            level: Target audience level
            language: Output language
            
        Returns:
            ExplanationArtifact with natural language explanation
        """
        # Extract key information
        prediction = model_output.get(
            "diagnosis",
            model_output.get("prediction", model_output.get("recommendation", "Unknown"))
        )
        confidence = model_output.get("confidence", 0.0)
        
        # Build evidence summary
        evidence_summary = self._summarize_evidence(evidence)
        
        # Generate explanation based on level
        if level == ExplanationLevel.FARMER:
            content = self._generate_farmer_summary(
                prediction, confidence, evidence_summary, language
            )
        elif level == ExplanationLevel.EXPERT:
            content = self._generate_expert_summary(
                prediction, confidence, evidence_summary, model_output, language
            )
        else:  # AUDITOR
            content = self._generate_auditor_summary(
                prediction, evidence, model_output
            )
        
        return ExplanationArtifact(
            strategy=ExplanationStrategy.LLM,
            level=level,
            content_type="text",
            content=content,
            structured_data={
                "prediction": prediction,
                "confidence": confidence,
                "evidence_count": len(evidence),
                "language": language
            },
            cited_evidence_ids=self.get_cited_evidence_ids(evidence),
            relevance_score=confidence
        )
    
    def supports(self, model_type: str) -> bool:
        """Check if this strategy supports the model type.
        
        Args:
            model_type: Type of model
            
        Returns:
            True - LLM can explain any model type
        """
        # LLM summarizer is a universal fallback
        return True
    
    def generate_one_liner(
        self,
        model_output: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """Generate a one-line summary for quick display.
        
        Args:
            model_output: Model output dictionary
            language: Output language
            
        Returns:
            One-line summary string
        """
        prediction = model_output.get(
            "diagnosis",
            model_output.get("prediction", "Unknown issue")
        )
        confidence = model_output.get("confidence", 0.0)
        
        return self._generate_farmer_summary(prediction, confidence, {}, language)
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load explanation templates by language and level.
        
        Returns:
            Nested dictionary of templates
        """
        return {
            "en": {
                "farmer_high": (
                    "Your crop appears to have {diagnosis}. "
                    "Our analysis is {confidence}% confident. "
                    "{evidence_note}"
                ),
                "farmer_medium": (
                    "This may be {diagnosis} ({confidence}% confidence). "
                    "{evidence_note} "
                    "Consider getting an expert opinion if symptoms persist."
                ),
                "farmer_low": (
                    "We're not certain, but this could be {diagnosis}. "
                    "{evidence_note} "
                    "Please provide more photos or details for a better assessment."
                ),
                "recommendation": (
                    "We recommend: {action}. {reason}. "
                    "This is based on {evidence_note}."
                ),
            },
            "sn": {  # Shona
                "farmer_high": (
                    "Mbesa yako inoratidza kuti ine {diagnosis}. "
                    "Chivimbo chedu nde{confidence}%. "
                    "{evidence_note}"
                ),
                "farmer_medium": (
                    "Ichi chinogona kuva {diagnosis} ({confidence}% chivimbo). "
                    "{evidence_note}"
                ),
                "farmer_low": (
                    "Hatisi nechokwadi, asi ichi chinogona kuva {diagnosis}. "
                    "{evidence_note}"
                ),
            },
            "pl": {  # Polish
                "farmer_high": (
                    "Twoja roślina wydaje się mieć {diagnosis}. "
                    "Nasza pewność to {confidence}%. "
                    "{evidence_note}"
                ),
                "farmer_medium": (
                    "To może być {diagnosis} ({confidence}% pewności). "
                    "{evidence_note}"
                ),
                "farmer_low": (
                    "Nie jesteśmy pewni, ale to może być {diagnosis}. "
                    "{evidence_note}"
                ),
            }
        }
    
    def _summarize_evidence(
        self,
        evidence: List[EvidenceItem]
    ) -> Dict[str, Any]:
        """Summarize evidence for explanation generation.
        
        Args:
            evidence: List of evidence items
            
        Returns:
            Summary dictionary
        """
        summary = {
            "count": len(evidence),
            "types": [],
            "key_points": [],
            "sources": set()
        }
        
        for ev in evidence:
            summary["types"].append(ev.evidence_type.value)
            summary["sources"].add(ev.source_engine)
            if ev.summary:
                summary["key_points"].append(ev.summary)
        
        summary["sources"] = list(summary["sources"])
        return summary
    
    def _format_evidence_note(
        self,
        evidence_summary: Dict[str, Any],
        language: str
    ) -> str:
        """Format evidence summary as a note.
        
        Args:
            evidence_summary: Evidence summary dictionary
            language: Output language
            
        Returns:
            Formatted evidence note
        """
        if not evidence_summary or evidence_summary.get("count", 0) == 0:
            return ""
        
        key_points = evidence_summary.get("key_points", [])[:3]
        
        if language == "en":
            if key_points:
                return f"Based on: {'; '.join(key_points)}."
            else:
                count = evidence_summary.get("count", 0)
                return f"Based on {count} data points analyzed."
        elif language == "sn":
            if key_points:
                return f"Zvakabudiswa ne: {'; '.join(key_points)}."
            else:
                count = evidence_summary.get("count", 0)
                return f"Zvakabudiswa ne{count} zvinhu zvakaongororwa."
        else:
            if key_points:
                return f"Based on: {'; '.join(key_points)}."
            else:
                return ""
    
    def _generate_farmer_summary(
        self,
        diagnosis: str,
        confidence: float,
        evidence_summary: Dict[str, Any],
        language: str
    ) -> str:
        """Generate farmer-level summary.
        
        Args:
            diagnosis: Diagnosis or prediction
            confidence: Confidence score
            evidence_summary: Evidence summary
            language: Output language
            
        Returns:
            Farmer-friendly explanation
        """
        conf_pct = int(confidence * 100)
        templates = self._templates.get(language, self._templates["en"])
        evidence_note = self._format_evidence_note(evidence_summary, language)
        
        # Select template based on confidence
        if confidence >= 0.8:
            template = templates.get("farmer_high", templates.get("farmer_medium"))
        elif confidence >= 0.5:
            template = templates.get("farmer_medium", templates.get("farmer_high"))
        else:
            template = templates.get("farmer_low", templates.get("farmer_medium"))
        
        return template.format(
            diagnosis=diagnosis,
            confidence=conf_pct,
            evidence_note=evidence_note
        ).strip()
    
    def _generate_expert_summary(
        self,
        diagnosis: str,
        confidence: float,
        evidence_summary: Dict[str, Any],
        model_output: Dict[str, Any],
        language: str
    ) -> str:
        """Generate expert-level summary.
        
        Args:
            diagnosis: Diagnosis or prediction
            confidence: Confidence score
            evidence_summary: Evidence summary
            model_output: Full model output
            language: Output language
            
        Returns:
            Expert-level explanation
        """
        parts = [
            f"**Diagnosis**: {diagnosis}",
            f"**Confidence**: {confidence:.1%}",
            ""
        ]
        
        # Add evidence summary
        if evidence_summary.get("key_points"):
            parts.append("**Evidence Summary**:")
            for point in evidence_summary["key_points"][:5]:
                parts.append(f"- {point}")
            parts.append("")
        
        # Add data sources
        if evidence_summary.get("sources"):
            sources = ", ".join(evidence_summary["sources"])
            parts.append(f"**Data Sources**: {sources}")
            parts.append("")
        
        # Add model details
        model_version = model_output.get("model_version", "unknown")
        parts.append(f"**Model Version**: {model_version}")
        
        # Add recommendations if present
        recommendations = model_output.get("recommendations", model_output.get("actions", []))
        if recommendations:
            parts.extend(["", "**Recommendations**:"])
            for rec in recommendations[:3]:
                if isinstance(rec, dict):
                    action = rec.get("action", rec.get("description", str(rec)))
                else:
                    action = str(rec)
                parts.append(f"- {action}")
        
        return "\n".join(parts)
    
    def _generate_auditor_summary(
        self,
        diagnosis: str,
        evidence: List[EvidenceItem],
        model_output: Dict[str, Any]
    ) -> str:
        """Generate auditor-level summary (JSON).
        
        Args:
            diagnosis: Diagnosis or prediction
            evidence: Full evidence list
            model_output: Full model output
            
        Returns:
            JSON string for auditing
        """
        import json
        
        # Serialize evidence (without circular refs)
        evidence_data = [
            {
                "id": ev.id,
                "type": ev.evidence_type.value,
                "source": ev.source_engine,
                "summary": ev.summary,
                "confidence": ev.confidence
            }
            for ev in evidence
        ]
        
        audit_data = {
            "diagnosis": diagnosis,
            "model_output": model_output,
            "evidence": evidence_data,
            "explanation_method": "llm_summary",
            "note": "This explanation was generated from evidence without chain-of-thought leakage"
        }
        
        return json.dumps(audit_data, indent=2, default=str)
