"""AuditService - Manages audit traces for Trust Engine compliance.

This service:
- Creates and updates audit trace entries
- Supports Trust Engine queries
- Maintains immutable records
- Generates signatures for compliance
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from ..models.audit_trace import FeedbackAuditTrace, AuditStep
from ..models.feedback_event import FeedbackEvent
from ..models.weighted_feedback import WeightedFeedback
from ..models.learning_signal import LearningSignal
from ..config import settings

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing feedback audit traces.
    
    Required for Trust Engine audits and data governance.
    All records are immutable and append-only.
    """
    
    def __init__(self):
        """Initialize audit service."""
        self._trace_store: Dict[str, FeedbackAuditTrace] = {}
        self._step_store: Dict[str, List[AuditStep]] = {}
    
    async def create_trace(
        self,
        event: FeedbackEvent,
    ) -> FeedbackAuditTrace:
        """Create a new audit trace for a feedback event.
        
        Args:
            event: FeedbackEvent to trace
            
        Returns:
            New FeedbackAuditTrace
        """
        trace = FeedbackAuditTrace(
            source_feedback_id=event.feedback_id,
            recommendation_id=event.recommendation_id,
            correlation_id=event.correlation_id,
            status="processing",
        )
        
        # Add initial step
        step = AuditStep(
            step_number=1,
            step_type="received",
            description=f"Received {event.feedback_type} feedback from {event.source_engine}",
            input_artifact_id=event.feedback_id,
            input_artifact_type="FeedbackEvent",
            values_after={
                "feedback_id": event.feedback_id,
                "feedback_type": event.feedback_type,
                "region_code": event.region_code,
                "user_id": event.user_id,
            },
            success=True,
        )
        
        trace.steps.append(step)
        
        # Store
        self._trace_store[trace.trace_id] = trace
        self._step_store[trace.trace_id] = [step]
        
        logger.info(
            f"Created audit trace {trace.trace_id} for feedback {event.feedback_id}",
            extra={"correlation_id": trace.correlation_id}
        )
        
        return trace
    
    async def add_validation_step(
        self,
        trace_id: str,
        is_valid: bool,
        validation_details: Dict[str, Any],
    ) -> AuditStep:
        """Add validation step to trace.
        
        Args:
            trace_id: Trace ID
            is_valid: Whether validation passed
            validation_details: Validation result details
            
        Returns:
            New AuditStep
        """
        trace = self._trace_store.get(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        step = AuditStep(
            step_number=len(trace.steps) + 1,
            step_type="validated",
            description="Validation completed" if is_valid else "Validation failed",
            success=is_valid,
            error_message=None if is_valid else "Validation failed",
            values_before={"status": "pending_validation"},
            values_after={
                "is_valid": is_valid,
                "is_duplicate": validation_details.get("is_duplicate", False),
                "is_contradiction": validation_details.get("is_contradiction", False),
                "is_noise": validation_details.get("is_noise", False),
            },
            transformation_applied="ValidationService.validate",
            transformation_params=validation_details,
        )
        
        trace.steps.append(step)
        self._step_store[trace_id].append(step)
        
        return step
    
    async def add_weighting_step(
        self,
        trace_id: str,
        weighted: WeightedFeedback,
    ) -> AuditStep:
        """Add weighting step to trace.
        
        Args:
            trace_id: Trace ID
            weighted: WeightedFeedback produced
            
        Returns:
            New AuditStep
        """
        trace = self._trace_store.get(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        step = AuditStep(
            step_number=len(trace.steps) + 1,
            step_type="weighted",
            description=f"Computed weight: {weighted.final_weight:.3f}",
            input_artifact_id=weighted.source_feedback_id,
            input_artifact_type="FeedbackEvent",
            output_artifact_id=weighted.weighted_id,
            output_artifact_type="WeightedFeedback",
            success=True,
            values_before={"raw_feedback": True},
            values_after={
                "final_weight": weighted.final_weight,
                "trust_score": weighted.trust_score,
                "is_flagged": weighted.is_flagged,
            },
            transformation_applied="WeightingService.compute_weight",
            transformation_params={
                "base_confidence": weighted.base_confidence,
                "farmer_experience_factor": weighted.farmer_experience_factor,
                "historical_accuracy_factor": weighted.historical_accuracy_factor,
                "model_confidence_factor": weighted.model_confidence_factor,
                "environmental_stability_factor": weighted.environmental_stability_factor,
            },
        )
        
        trace.steps.append(step)
        trace.weighted_feedback_id = weighted.weighted_id
        self._step_store[trace_id].append(step)
        
        return step
    
    async def add_flagging_step(
        self,
        trace_id: str,
        flag_id: str,
        flag_reasons: List[str],
    ) -> AuditStep:
        """Add flagging step to trace.
        
        Args:
            trace_id: Trace ID
            flag_id: Flag ID
            flag_reasons: List of flag reasons
            
        Returns:
            New AuditStep
        """
        trace = self._trace_store.get(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        step = AuditStep(
            step_number=len(trace.steps) + 1,
            step_type="flagged",
            description=f"Flagged for review: {', '.join(flag_reasons)}",
            output_artifact_id=flag_id,
            output_artifact_type="Flag",
            success=True,
            values_after={
                "flag_id": flag_id,
                "flag_reasons": flag_reasons,
            },
        )
        
        trace.steps.append(step)
        trace.flag_id = flag_id
        trace.status = "flagged"
        self._step_store[trace_id].append(step)
        
        return step
    
    async def add_signal_step(
        self,
        trace_id: str,
        signal: LearningSignal,
    ) -> AuditStep:
        """Add signal generation step to trace.
        
        Args:
            trace_id: Trace ID
            signal: LearningSignal generated
            
        Returns:
            New AuditStep
        """
        trace = self._trace_store.get(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        step = AuditStep(
            step_number=len(trace.steps) + 1,
            step_type="signal_generated",
            description=f"Generated {signal.signal_type.value} signal with strength {signal.signal_strength:.3f}",
            output_artifact_id=signal.signal_id,
            output_artifact_type="LearningSignal",
            success=True,
            values_after={
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type.value,
                "signal_strength": signal.signal_strength,
                "target_engine": signal.target_engine,
            },
            transformation_applied="SignalService.generate_signal",
        )
        
        trace.steps.append(step)
        trace.learning_signal_ids.append(signal.signal_id)
        self._step_store[trace_id].append(step)
        
        return step
    
    async def add_routing_step(
        self,
        trace_id: str,
        signal_id: str,
        stream: str,
        success: bool,
        error: Optional[str] = None,
    ) -> AuditStep:
        """Add routing step to trace.
        
        Args:
            trace_id: Trace ID
            signal_id: Routed signal ID
            stream: Target stream
            success: Whether routing succeeded
            error: Error message if failed
            
        Returns:
            New AuditStep
        """
        trace = self._trace_store.get(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        step = AuditStep(
            step_number=len(trace.steps) + 1,
            step_type="routed",
            description=f"Routed to {stream}" if success else f"Routing failed: {error}",
            input_artifact_id=signal_id,
            input_artifact_type="LearningSignal",
            success=success,
            error_message=error,
            values_after={
                "stream": stream,
                "routed": success,
            },
            transformation_applied="RoutingService.route_signal",
        )
        
        trace.steps.append(step)
        self._step_store[trace_id].append(step)
        
        return step
    
    async def complete_trace(
        self,
        trace_id: str,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> FeedbackAuditTrace:
        """Mark trace as completed.
        
        Args:
            trace_id: Trace ID
            status: Final status
            error_message: Error if failed
            
        Returns:
            Updated trace
        """
        trace = self._trace_store.get(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        now = datetime.utcnow()
        
        # Update trace
        trace.status = status
        trace.error_message = error_message
        trace.completed_at = now
        
        if trace.started_at:
            trace.total_duration_ms = (now - trace.started_at).total_seconds() * 1000
        
        # Generate signature if enabled
        if settings.ENABLE_AUDIT_LOGGING:
            trace.signature = self._generate_signature(trace)
            trace.signature_algorithm = "sha256"
        
        logger.info(
            f"Completed audit trace {trace_id} with status {status}",
            extra={"correlation_id": trace.correlation_id}
        )
        
        return trace
    
    async def get_trace(
        self,
        trace_id: str,
    ) -> Optional[FeedbackAuditTrace]:
        """Get trace by ID.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            FeedbackAuditTrace if found
        """
        return self._trace_store.get(trace_id)
    
    async def get_trace_by_feedback(
        self,
        feedback_id: str,
    ) -> Optional[FeedbackAuditTrace]:
        """Get trace by source feedback ID.
        
        Args:
            feedback_id: Source feedback ID
            
        Returns:
            FeedbackAuditTrace if found
        """
        for trace in self._trace_store.values():
            if trace.source_feedback_id == feedback_id:
                return trace
        return None
    
    async def get_traces_for_recommendation(
        self,
        recommendation_id: str,
    ) -> List[FeedbackAuditTrace]:
        """Get all traces for a recommendation.
        
        Args:
            recommendation_id: Recommendation ID
            
        Returns:
            List of traces
        """
        return [
            t for t in self._trace_store.values()
            if t.recommendation_id == recommendation_id
        ]
    
    async def query_traces(
        self,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[FeedbackAuditTrace]:
        """Query traces with filters.
        
        Args:
            status: Optional status filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Max results
            
        Returns:
            List of matching traces
        """
        traces = list(self._trace_store.values())
        
        if status:
            traces = [t for t in traces if t.status == status]
        
        if start_time:
            traces = [t for t in traces if t.started_at >= start_time]
        
        if end_time:
            traces = [t for t in traces if t.started_at <= end_time]
        
        # Sort by start time descending
        traces = sorted(traces, key=lambda t: t.started_at, reverse=True)
        
        return traces[:limit]
    
    def _generate_signature(self, trace: FeedbackAuditTrace) -> str:
        """Generate cryptographic signature for trace.
        
        Args:
            trace: Trace to sign
            
        Returns:
            Hex-encoded signature
        """
        # Create deterministic representation
        data = {
            "trace_id": trace.trace_id,
            "source_feedback_id": trace.source_feedback_id,
            "recommendation_id": trace.recommendation_id,
            "step_count": len(trace.steps),
            "status": trace.status,
            "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
        }
        
        # Hash
        content = json.dumps(data, sort_keys=True)
        signature = hashlib.sha256(content.encode()).hexdigest()
        
        return signature
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit service statistics.
        
        Returns:
            Dict with stats
        """
        traces = list(self._trace_store.values())
        
        by_status = {}
        for trace in traces:
            by_status[trace.status] = by_status.get(trace.status, 0) + 1
        
        total_steps = sum(len(t.steps) for t in traces)
        
        return {
            "total_traces": len(traces),
            "by_status": by_status,
            "total_steps": total_steps,
            "avg_steps_per_trace": total_steps / len(traces) if traces else 0,
        }
