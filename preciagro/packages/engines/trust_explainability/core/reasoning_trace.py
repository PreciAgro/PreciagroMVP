"""Reasoning Trace Composition Module.

Produces the canonical ReasoningTrace object -
single source of truth for trust and audits.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Self

from ..contracts.v1.schemas import (
    ReasoningTrace,
    EvidenceItem,
    ModelInfo,
    ExplanationArtifact,
    ConfidenceMetrics,
    SafetyCheckResult,
)
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class ReasoningTraceBuilder:
    """Builder for composing canonical ReasoningTrace objects.

    Uses the builder pattern to construct immutable traces
    containing all information needed for trust and audits.
    """

    def __init__(self) -> None:
        """Initialize trace builder."""
        self.settings = get_settings()
        self._reset()

    def _reset(self) -> None:
        """Reset builder state."""
        self._trace_id: Optional[str] = None
        self._request_id: Optional[str] = None
        self._input_refs: Dict[str, str] = {}
        self._models: List[ModelInfo] = []
        self._evidence: List[EvidenceItem] = []
        self._explanations: List[ExplanationArtifact] = []
        self._confidence: Optional[ConfidenceMetrics] = None
        self._safety_check: Optional[SafetyCheckResult] = None
        self._decision_id: Optional[str] = None
        self._decision_type: Optional[str] = None
        self._decision_summary: Optional[str] = None
        self._metadata: Dict[str, Any] = {}

    def create(self, request_id: str) -> Self:
        """Start building a new trace.

        Args:
            request_id: Original request ID

        Returns:
            Self for chaining
        """
        self._reset()
        self._request_id = request_id
        return self

    def with_trace_id(self, trace_id: str) -> Self:
        """Set explicit trace ID.

        Args:
            trace_id: Trace ID to use

        Returns:
            Self for chaining
        """
        self._trace_id = trace_id
        return self

    def add_input_ref(self, key: str, ref: str) -> Self:
        """Add input reference.

        Args:
            key: Reference key (e.g., "image_id", "sensor_data")
            ref: Reference URI or ID

        Returns:
            Self for chaining
        """
        self._input_refs[key] = ref
        return self

    def add_model(self, model: ModelInfo) -> Self:
        """Add a model involved in the decision.

        Args:
            model: ModelInfo object

        Returns:
            Self for chaining
        """
        self._models.append(model)
        return self

    def add_models(self, models: List[ModelInfo]) -> Self:
        """Add multiple models.

        Args:
            models: List of ModelInfo objects

        Returns:
            Self for chaining
        """
        self._models.extend(models)
        return self

    def add_evidence(self, evidence: List[EvidenceItem]) -> Self:
        """Add evidence items.

        Args:
            evidence: List of EvidenceItem objects

        Returns:
            Self for chaining
        """
        self._evidence.extend(evidence)
        return self

    def add_explanation(self, explanation: ExplanationArtifact) -> Self:
        """Add an explanation artifact.

        Args:
            explanation: ExplanationArtifact object

        Returns:
            Self for chaining
        """
        self._explanations.append(explanation)
        return self

    def add_explanations(self, explanations: List[ExplanationArtifact]) -> Self:
        """Add multiple explanations.

        Args:
            explanations: List of ExplanationArtifact objects

        Returns:
            Self for chaining
        """
        self._explanations.extend(explanations)
        return self

    def set_confidence(self, confidence: ConfidenceMetrics) -> Self:
        """Set confidence metrics.

        Args:
            confidence: ConfidenceMetrics object

        Returns:
            Self for chaining
        """
        self._confidence = confidence
        return self

    def set_safety_check(self, safety_check: SafetyCheckResult) -> Self:
        """Set safety check result.

        Args:
            safety_check: SafetyCheckResult object

        Returns:
            Self for chaining
        """
        self._safety_check = safety_check
        return self

    def set_decision(self, decision_id: str, decision_type: str, summary: str) -> Self:
        """Set decision information.

        Args:
            decision_id: Decision/recommendation ID
            decision_type: Type of decision
            summary: Brief decision summary

        Returns:
            Self for chaining
        """
        self._decision_id = decision_id
        self._decision_type = decision_type
        self._decision_summary = summary
        return self

    def add_metadata(self, key: str, value: Any) -> Self:
        """Add metadata.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for chaining
        """
        self._metadata[key] = value
        return self

    def build(self) -> ReasoningTrace:
        """Build the immutable ReasoningTrace object.

        Returns:
            Completed ReasoningTrace

        Raises:
            ValueError: If required fields are missing
        """
        if not self._request_id:
            raise ValueError("request_id is required")

        # Generate feedback URL
        feedback_url = f"/api/v1/feedback?trace_id={self._trace_id or 'pending'}"

        trace = ReasoningTrace(
            trace_id=self._trace_id,  # Will be auto-generated if None
            request_id=self._request_id,
            created_at=datetime.utcnow(),
            input_refs=self._input_refs,
            models=self._models,
            evidence=self._evidence,
            explanations=self._explanations,
            confidence=self._confidence,
            safety_check=self._safety_check,
            decision_id=self._decision_id,
            decision_type=self._decision_type,
            decision_summary=self._decision_summary,
            engine_version="1.0.0",
            feedback_enabled=True,
            feedback_url=feedback_url,
            metadata=self._metadata,
        )

        # Update feedback URL with actual trace ID
        trace.feedback_url = f"/api/v1/feedback?trace_id={trace.trace_id}"

        logger.info(
            f"Built reasoning trace {trace.trace_id} for request {self._request_id} "
            f"with {len(self._evidence)} evidence items and {len(self._explanations)} explanations"
        )

        return trace

    def sign(self, trace: ReasoningTrace) -> str:
        """Generate cryptographic signature for audit compliance.

        Note: In MVP, this generates a hash-based signature.
        In production, use proper cryptographic signing with HSM.

        Args:
            trace: Trace to sign

        Returns:
            Signature string
        """
        if not self.settings.feature_audit_signatures:
            logger.debug("Audit signatures disabled, returning hash-only signature")

        # Serialize trace for signing (excluding signature fields)
        trace_dict = trace.model_dump(exclude={"signature", "signature_algorithm"})
        content = json.dumps(trace_dict, sort_keys=True, default=str)

        # Generate hash-based signature
        signature = hashlib.sha256(content.encode()).hexdigest()

        return f"sha256:{signature}"


class TraceStore:
    """In-memory store for reasoning traces.

    MVP implementation - in production, use PostgreSQL or similar.
    """

    def __init__(self) -> None:
        """Initialize trace store."""
        self._traces: Dict[str, ReasoningTrace] = {}
        self._by_request: Dict[str, List[str]] = {}

    def store(self, trace: ReasoningTrace) -> str:
        """Store a trace and return its ID.

        Args:
            trace: Trace to store

        Returns:
            Trace ID
        """
        self._traces[trace.trace_id] = trace

        # Index by request ID
        if trace.request_id not in self._by_request:
            self._by_request[trace.request_id] = []
        self._by_request[trace.request_id].append(trace.trace_id)

        logger.debug(f"Stored trace {trace.trace_id}")
        return trace.trace_id

    def get(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Retrieve a trace by ID.

        Args:
            trace_id: Trace ID

        Returns:
            ReasoningTrace if found, None otherwise
        """
        return self._traces.get(trace_id)

    def get_by_request(self, request_id: str) -> List[ReasoningTrace]:
        """Get all traces for a request.

        Args:
            request_id: Request ID

        Returns:
            List of traces for the request
        """
        trace_ids = self._by_request.get(request_id, [])
        return [self._traces[tid] for tid in trace_ids if tid in self._traces]

    def delete(self, trace_id: str) -> bool:
        """Delete a trace (for compliance/GDPR).

        Args:
            trace_id: Trace ID to delete

        Returns:
            True if deleted, False if not found
        """
        trace = self._traces.pop(trace_id, None)
        if trace:
            # Remove from request index
            if trace.request_id in self._by_request:
                self._by_request[trace.request_id] = [
                    tid for tid in self._by_request[trace.request_id] if tid != trace_id
                ]
            logger.info(f"Deleted trace {trace_id}")
            return True
        return False

    def count(self) -> int:
        """Get total number of stored traces.

        Returns:
            Trace count
        """
        return len(self._traces)


# Singleton store instance
_trace_store: Optional[TraceStore] = None


def get_trace_store() -> TraceStore:
    """Get singleton trace store instance."""
    global _trace_store
    if _trace_store is None:
        _trace_store = TraceStore()
    return _trace_store
