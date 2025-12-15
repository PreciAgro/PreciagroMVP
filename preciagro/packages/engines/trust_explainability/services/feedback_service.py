"""Feedback Service.

Captures and routes user feedback on explanations.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..contracts.v1.schemas import FeedbackPayload, ReasoningTrace
from ..core.reasoning_trace import get_trace_store

logger = logging.getLogger(__name__)


class FeedbackService:
    """Feedback capture and routing service.

    Attaches feedback to traces and routes to Feedback & Learning Engine.
    """

    def __init__(self) -> None:
        """Initialize feedback service."""
        self._feedback_store: Dict[str, List[FeedbackPayload]] = {}
        self._feedback_engine_url: Optional[str] = None
        logger.info("FeedbackService initialized")

    async def submit(self, feedback: FeedbackPayload) -> Dict[str, Any]:
        """Submit feedback for a trace.

        Args:
            feedback: Feedback payload

        Returns:
            Submission result
        """
        trace_id = feedback.trace_id

        # Validate trace exists
        trace_store = get_trace_store()
        trace = trace_store.get(trace_id)

        if not trace:
            logger.warning(f"Feedback submitted for unknown trace: {trace_id}")
            return {"success": False, "message": f"Trace {trace_id} not found"}

        # Store feedback
        if trace_id not in self._feedback_store:
            self._feedback_store[trace_id] = []

        self._feedback_store[trace_id].append(feedback)

        logger.info(
            f"Received {feedback.feedback_type} feedback for trace {trace_id} "
            f"(rating: {feedback.rating})"
        )

        # Route to learning engine (async in production)
        await self._route_to_learning_engine(feedback, trace)

        return {
            "success": True,
            "message": "Feedback recorded",
            "trace_id": trace_id,
            "feedback_type": feedback.feedback_type,
        }

    async def get_feedback(self, trace_id: str) -> List[FeedbackPayload]:
        """Get all feedback for a trace.

        Args:
            trace_id: Trace ID

        Returns:
            List of feedback payloads
        """
        return self._feedback_store.get(trace_id, [])

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics.

        Returns:
            Statistics dictionary
        """
        total_feedback = sum(len(fb) for fb in self._feedback_store.values())

        type_counts: Dict[str, int] = {}
        rating_sum = 0
        rating_count = 0

        for feedbacks in self._feedback_store.values():
            for fb in feedbacks:
                type_counts[fb.feedback_type] = type_counts.get(fb.feedback_type, 0) + 1
                if fb.rating:
                    rating_sum += fb.rating
                    rating_count += 1

        avg_rating = rating_sum / rating_count if rating_count > 0 else None

        return {
            "total_feedback": total_feedback,
            "traces_with_feedback": len(self._feedback_store),
            "feedback_by_type": type_counts,
            "average_rating": avg_rating,
        }

    async def _route_to_learning_engine(
        self, feedback: FeedbackPayload, trace: ReasoningTrace
    ) -> None:
        """Route feedback to Feedback & Learning Engine.

        Args:
            feedback: Feedback payload
            trace: Associated reasoning trace
        """
        if not self._feedback_engine_url:
            logger.debug("Feedback engine URL not configured, skipping routing")
            return

        # In production, this would make an HTTP call to the learning engine
        # For MVP, we just log it
        logger.info(
            f"Routing feedback to learning engine: "
            f"type={feedback.feedback_type}, "
            f"trace={trace.trace_id}, "
            f"decision={trace.decision_type}"
        )

        # Prepare payload for learning engine
        learning_payload = {
            "feedback_type": feedback.feedback_type,
            "rating": feedback.rating,
            "trace_id": trace.trace_id,
            "decision_id": trace.decision_id,
            "decision_type": trace.decision_type,
            "models_involved": [m.model_id for m in trace.models],
            "confidence": trace.confidence.overall_confidence if trace.confidence else None,
            "safety_status": trace.safety_check.status.value if trace.safety_check else None,
            "correction": feedback.suggested_correction,
            "timestamp": feedback.submitted_at.isoformat(),
        }

        # TODO: Send to learning engine
        # async with httpx.AsyncClient() as client:
        #     await client.post(self._feedback_engine_url, json=learning_payload)

        logger.debug(f"Learning payload prepared: {learning_payload}")
