"""Example-Based Retrieval Strategy.

Retrieves similar historical cases to support explanations
with concrete examples from past diagnoses.
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .base import BaseExplainer
from ..contracts.v1.schemas import EvidenceItem, ExplanationArtifact
from ..contracts.v1.enums import ExplanationLevel, ExplanationStrategy

logger = logging.getLogger(__name__)

# Try to import numpy for vector operations
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


@dataclass
class HistoricalCase:
    """A historical case for comparison."""

    case_id: str
    timestamp: datetime
    diagnosis: str
    confidence: float
    similarity: float
    features: Dict[str, Any]
    treatment: Optional[str] = None
    outcome: Optional[str] = None
    region: Optional[str] = None
    crop: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "timestamp": self.timestamp.isoformat(),
            "diagnosis": self.diagnosis,
            "confidence": self.confidence,
            "similarity": self.similarity,
            "treatment": self.treatment,
            "outcome": self.outcome,
            "region": self.region,
            "crop": self.crop,
        }


class ExampleRetriever(BaseExplainer):
    """Retrieves similar historical cases for example-based explanations.

    Uses vector similarity to find cases with similar:
    - Feature profiles
    - Diagnoses
    - Outcomes
    """

    @property
    def strategy_type(self) -> ExplanationStrategy:
        return ExplanationStrategy.EXAMPLE

    def __init__(self) -> None:
        """Initialize example retriever."""
        self._case_store: List[HistoricalCase] = []
        self._embeddings: Dict[str, List[float]] = {}
        self._initialize_sample_cases()
        logger.info(f"ExampleRetriever initialized with {len(self._case_store)} cases")

    def _initialize_sample_cases(self) -> None:
        """Initialize with sample historical cases for demo."""
        sample_cases = [
            HistoricalCase(
                case_id="case_001",
                timestamp=datetime(2024, 3, 15),
                diagnosis="leaf_blight",
                confidence=0.92,
                similarity=0.0,
                features={"pH": 5.8, "nitrogen": 45, "moisture": 72},
                treatment="Copper fungicide 2kg/ha",
                outcome="resolved_7_days",
                region="ZW-HA",
                crop="maize",
            ),
            HistoricalCase(
                case_id="case_002",
                timestamp=datetime(2024, 4, 2),
                diagnosis="rust",
                confidence=0.88,
                similarity=0.0,
                features={"pH": 6.2, "nitrogen": 38, "moisture": 65},
                treatment="Triazole fungicide",
                outcome="resolved_14_days",
                region="ZW-HA",
                crop="maize",
            ),
            HistoricalCase(
                case_id="case_003",
                timestamp=datetime(2024, 4, 20),
                diagnosis="powdery_mildew",
                confidence=0.95,
                similarity=0.0,
                features={"pH": 6.5, "nitrogen": 52, "moisture": 80},
                treatment="Sulfur spray",
                outcome="resolved_10_days",
                region="ZW-MN",
                crop="tomato",
            ),
            HistoricalCase(
                case_id="case_004",
                timestamp=datetime(2024, 5, 10),
                diagnosis="nitrogen_deficiency",
                confidence=0.85,
                similarity=0.0,
                features={"pH": 6.0, "nitrogen": 15, "moisture": 55},
                treatment="Urea fertilizer 50kg/ha",
                outcome="improved_21_days",
                region="ZW-HA",
                crop="maize",
            ),
            HistoricalCase(
                case_id="case_005",
                timestamp=datetime(2024, 6, 1),
                diagnosis="leaf_blight",
                confidence=0.78,
                similarity=0.0,
                features={"pH": 5.5, "nitrogen": 42, "moisture": 78},
                treatment="Copper fungicide 2.5kg/ha",
                outcome="resolved_10_days",
                region="ZW-BU",
                crop="maize",
            ),
        ]

        self._case_store = sample_cases

        # Pre-compute embeddings
        for case in sample_cases:
            embedding = self._embed_case(case)
            self._embeddings[case.case_id] = embedding

    def explain(
        self,
        evidence: List[EvidenceItem],
        model_output: Dict[str, Any],
        level: ExplanationLevel = ExplanationLevel.FARMER,
        language: str = "en",
    ) -> ExplanationArtifact:
        """Generate example-based explanation.

        Args:
            evidence: Evidence items
            model_output: Model output to explain
            level: Target audience level
            language: Output language

        Returns:
            ExplanationArtifact with similar cases
        """
        # Extract query features
        features = self._extract_features(evidence, model_output)
        diagnosis = model_output.get("diagnosis", model_output.get("prediction", ""))

        # Find similar cases
        similar_cases = self.find_similar_cases(features=features, diagnosis=diagnosis, top_k=3)

        # Format explanation
        if level == ExplanationLevel.FARMER:
            content = self._format_farmer_examples(similar_cases, language)
            content_type = "text"
        elif level == ExplanationLevel.EXPERT:
            content = self._format_expert_examples(similar_cases, features)
            content_type = "text"
        else:
            content = self._format_auditor_examples(similar_cases, features)
            content_type = "structured"

        return ExplanationArtifact(
            strategy=ExplanationStrategy.EXAMPLE,
            level=level,
            content_type=content_type,
            content=content,
            structured_data={
                "similar_cases": [c.to_dict() for c in similar_cases],
                "query_features": features,
                "query_diagnosis": diagnosis,
            },
            cited_evidence_ids=self.get_cited_evidence_ids(evidence),
            relevance_score=similar_cases[0].similarity if similar_cases else 0.0,
        )

    def supports(self, model_type: str) -> bool:
        """Check if this strategy supports the model type.

        Args:
            model_type: Type of model

        Returns:
            True - examples work for any model type
        """
        return True

    def find_similar_cases(
        self,
        features: Dict[str, Any],
        diagnosis: str = "",
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[HistoricalCase]:
        """Find similar historical cases.

        Args:
            features: Query feature values
            diagnosis: Query diagnosis (optional, boosts matching cases)
            top_k: Number of cases to return
            filters: Optional filters (region, crop, date range)

        Returns:
            List of similar cases with similarity scores
        """
        if not self._case_store:
            return []

        # Apply filters
        candidates = self._case_store
        if filters:
            candidates = self._apply_filters(candidates, filters)

        # Compute query embedding
        query_embedding = self._embed_features(features)

        # Compute similarities
        scored_cases: List[Tuple[float, HistoricalCase]] = []

        for case in candidates:
            case_embedding = self._embeddings.get(case.case_id)
            if case_embedding is None:
                case_embedding = self._embed_case(case)

            similarity = self._cosine_similarity(query_embedding, case_embedding)

            # Boost if diagnosis matches
            if diagnosis and case.diagnosis.lower() == diagnosis.lower():
                similarity = min(similarity * 1.2, 1.0)

            scored_cases.append((similarity, case))

        # Sort by similarity
        scored_cases.sort(key=lambda x: x[0], reverse=True)

        # Create copies with similarity scores
        results = []
        for sim, case in scored_cases[:top_k]:
            case_copy = HistoricalCase(
                case_id=case.case_id,
                timestamp=case.timestamp,
                diagnosis=case.diagnosis,
                confidence=case.confidence,
                similarity=round(sim, 3),
                features=case.features,
                treatment=case.treatment,
                outcome=case.outcome,
                region=case.region,
                crop=case.crop,
            )
            results.append(case_copy)

        return results

    def add_case(self, case: HistoricalCase) -> None:
        """Add a new historical case to the store.

        Args:
            case: Historical case to add
        """
        self._case_store.append(case)
        self._embeddings[case.case_id] = self._embed_case(case)
        logger.debug(f"Added case {case.case_id} to store")

    def _embed_case(self, case: HistoricalCase) -> List[float]:
        """Embed a case for similarity search.

        Args:
            case: Historical case

        Returns:
            Embedding vector
        """
        # Simple feature-based embedding
        # In production, use sentence transformers or similar
        return self._embed_features(case.features)

    def _embed_features(self, features: Dict[str, Any]) -> List[float]:
        """Create embedding from features.

        Simple normalized feature vector.
        In production, use proper embeddings.

        Args:
            features: Feature dictionary

        Returns:
            Embedding vector
        """
        # Define standard feature order and normalization
        feature_spec = {
            "pH": (0, 14, 7.0),  # min, max, default
            "nitrogen": (0, 200, 50),
            "phosphorus": (0, 100, 30),
            "potassium": (0, 300, 100),
            "moisture": (0, 100, 50),
            "temperature": (0, 50, 25),
            "humidity": (0, 100, 60),
        }

        embedding = []
        for feature, (min_val, max_val, default) in feature_spec.items():
            value = features.get(feature, default)
            if isinstance(value, (int, float)):
                # Normalize to 0-1
                normalized = (value - min_val) / (max_val - min_val)
                normalized = max(0, min(1, normalized))
            else:
                normalized = 0.5  # Default for missing
            embedding.append(normalized)

        return embedding

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        if HAS_NUMPY:
            a = np.array(vec1)
            b = np.array(vec2)
            dot = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot / (norm_a * norm_b))
        else:
            # Pure Python fallback
            dot = sum(a * b for a, b in zip(vec1, vec2))
            norm_a = sum(a * a for a in vec1) ** 0.5
            norm_b = sum(b * b for b in vec2) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

    def _apply_filters(
        self, cases: List[HistoricalCase], filters: Dict[str, Any]
    ) -> List[HistoricalCase]:
        """Apply filters to case list.

        Args:
            cases: Cases to filter
            filters: Filter criteria

        Returns:
            Filtered cases
        """
        result = cases

        if "region" in filters and filters["region"]:
            result = [c for c in result if c.region == filters["region"]]

        if "crop" in filters and filters["crop"]:
            result = [c for c in result if c.crop == filters["crop"]]

        if "min_confidence" in filters:
            result = [c for c in result if c.confidence >= filters["min_confidence"]]

        return result

    def _extract_features(
        self, evidence: List[EvidenceItem], model_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract features from evidence and model output."""
        features: Dict[str, Any] = {}

        for key in ["features", "inputs", "data"]:
            if key in model_output and isinstance(model_output[key], dict):
                features.update(model_output[key])

        for ev in evidence:
            if ev.metadata:
                for key in ["soil", "weather", "features"]:
                    if key in ev.metadata and isinstance(ev.metadata[key], dict):
                        features.update(ev.metadata[key])

        return features

    def _format_farmer_examples(self, cases: List[HistoricalCase], language: str) -> str:
        """Format examples for farmer audience."""
        if not cases:
            return "No similar historical cases found."

        lines = ["Based on similar cases from the past:"]

        for i, case in enumerate(cases[:3], 1):
            date_str = case.timestamp.strftime("%B %Y")
            lines.append(
                f"{i}. In {date_str}, a similar case of {case.diagnosis} "
                f"was treated with {case.treatment or 'standard treatment'}. "
                f"Outcome: {case.outcome or 'successful'}."
            )

        return "\n".join(lines)

    def _format_expert_examples(
        self, cases: List[HistoricalCase], query_features: Dict[str, Any]
    ) -> str:
        """Format examples for expert audience."""
        lines = ["**Similar Historical Cases**", ""]

        for case in cases:
            lines.extend(
                [
                    f"### Case {case.case_id} ({case.similarity:.0%} similar)",
                    f"- **Date**: {case.timestamp.strftime('%Y-%m-%d')}",
                    f"- **Diagnosis**: {case.diagnosis} ({case.confidence:.0%} confidence)",
                    f"- **Treatment**: {case.treatment or 'N/A'}",
                    f"- **Outcome**: {case.outcome or 'N/A'}",
                    f"- **Region**: {case.region}, **Crop**: {case.crop}",
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_auditor_examples(
        self, cases: List[HistoricalCase], query_features: Dict[str, Any]
    ) -> str:
        """Format examples for auditor (JSON)."""
        import json

        audit_data = {
            "query_features": query_features,
            "similar_cases": [c.to_dict() for c in cases],
            "retrieval_method": "cosine_similarity",
            "embedding_dim": len(self._embed_features({})),
        }

        return json.dumps(audit_data, indent=2, default=str)
