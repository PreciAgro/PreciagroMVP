"""RoutingService - Routes learning signals to downstream engine consumers.

This service:
- Routes signals to Redis Streams per engine consumer
- Implements exactly-once semantics where possible
- Handles dead-letter stream for failed messages
- Tracks correlation IDs for end-to-end tracing
"""

import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4
from dataclasses import dataclass, field

from ..models.learning_signal import LearningSignal
from ..contracts.downstream import LearningSignalOutput, FlaggedFeedbackOutput
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class RoutingResult:
    """Result of routing operation."""
    success: bool
    signal_ids: List[str]
    stream: str
    message_ids: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class RoutingService:
    """Service for routing learning signals to downstream engines.
    
    Routes to:
    - Evaluation & Benchmarking Engine
    - Model Orchestration Engine
    - PIE Lite (Product Insights Engine)
    - Human-in-the-Loop Review Tools
    
    Uses Redis Streams with:
    - Separate stream per consumer engine
    - Dead-letter stream for failures
    - Correlation ID tracking
    """
    
    def __init__(self, redis_client=None):
        """Initialize routing service.
        
        Args:
            redis_client: Optional Redis client (uses mock if None)
        """
        self._redis = redis_client
        self._message_store: Dict[str, List[Dict]] = {
            "evaluation": [],
            "model_orchestration": [],
            "pie": [],
            "hitl": [],
            "dead_letter": [],
        }
        self._routing_log: List[RoutingResult] = []
    
    async def route_signal(
        self,
        signal: LearningSignal,
    ) -> RoutingResult:
        """Route a single signal to its target engine(s).
        
        Args:
            signal: LearningSignal to route
            
        Returns:
            RoutingResult with status
        """
        targets = self._get_target_streams(signal.target_engine)
        
        results = []
        for stream in targets:
            result = await self._send_to_stream(stream, signal)
            results.append(result)
        
        # Aggregate results
        all_success = all(r.success for r in results)
        all_message_ids = []
        all_errors = []
        
        for r in results:
            all_message_ids.extend(r.message_ids)
            all_errors.extend(r.errors)
        
        final_result = RoutingResult(
            success=all_success,
            signal_ids=[signal.signal_id],
            stream=",".join(targets),
            message_ids=all_message_ids,
            errors=all_errors,
        )
        
        self._routing_log.append(final_result)
        
        if all_success:
            logger.info(
                f"Routed signal {signal.signal_id} to {targets}",
                extra={"correlation_id": signal.correlation_id}
            )
        else:
            logger.error(
                f"Failed to route signal {signal.signal_id}: {all_errors}",
                extra={"correlation_id": signal.correlation_id}
            )
        
        return final_result
    
    async def route_batch(
        self,
        signals: List[LearningSignal],
    ) -> RoutingResult:
        """Route a batch of signals.
        
        Args:
            signals: List of signals to route
            
        Returns:
            Aggregate RoutingResult
        """
        if not signals:
            return RoutingResult(
                success=True,
                signal_ids=[],
                stream="none",
            )
        
        results = []
        for signal in signals:
            result = await self.route_signal(signal)
            results.append(result)
        
        # Aggregate
        all_success = all(r.success for r in results)
        all_ids = [s.signal_id for s in signals]
        all_message_ids = []
        all_errors = []
        streams = set()
        
        for r in results:
            all_message_ids.extend(r.message_ids)
            all_errors.extend(r.errors)
            streams.add(r.stream)
        
        return RoutingResult(
            success=all_success,
            signal_ids=all_ids,
            stream=",".join(streams),
            message_ids=all_message_ids,
            errors=all_errors,
        )
    
    async def route_flagged(
        self,
        flagged: FlaggedFeedbackOutput,
    ) -> RoutingResult:
        """Route flagged feedback to HITL review.
        
        Args:
            flagged: Flagged feedback output
            
        Returns:
            RoutingResult
        """
        stream = settings.STREAM_HITL
        
        message = {
            "type": "flagged_feedback",
            "flag_id": flagged.flag_id,
            "feedback_id": flagged.feedback_id,
            "recommendation_id": flagged.recommendation_id,
            "flag_reason": flagged.flag_reason.value,
            "flag_severity": flagged.flag_severity,
            "flag_description": flagged.flag_description,
            "feedback_summary": flagged.feedback_summary,
            "computed_weight": flagged.computed_weight,
            "review_priority": flagged.review_priority,
            "correlation_id": flagged.correlation_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add to mock store
        self._message_store["hitl"].append(message)
        message_id = str(uuid4())
        
        result = RoutingResult(
            success=True,
            signal_ids=[flagged.flag_id],
            stream=stream,
            message_ids=[message_id],
        )
        
        self._routing_log.append(result)
        
        logger.info(
            f"Routed flagged feedback {flagged.flag_id} to HITL",
            extra={"correlation_id": flagged.correlation_id}
        )
        
        return result
    
    async def _send_to_stream(
        self,
        stream: str,
        signal: LearningSignal,
    ) -> RoutingResult:
        """Send signal to a specific stream.
        
        Args:
            stream: Target stream name
            signal: Signal to send
            
        Returns:
            RoutingResult for this stream
        """
        try:
            # Convert signal to output format
            output = self._to_output_format(signal)
            
            # Serialize
            message = {
                "type": "learning_signal",
                "signal_id": output.signal_id,
                "signal_type": output.signal_type.value,
                "signal_strength": output.signal_strength,
                "recommendation_id": output.recommendation_id,
                "target_engine": output.target_engine,
                "region_scope": output.region_scope,
                "feedback_count": output.feedback_count,
                "average_weight": output.average_weight,
                "confidence_score": output.confidence_score,
                "correlation_id": output.correlation_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            if self._redis:
                # Real Redis routing
                message_id = await self._redis.xadd(
                    stream,
                    {"data": json.dumps(message)},
                    maxlen=settings.REDIS_MAX_STREAM_LENGTH,
                )
            else:
                # Mock routing
                stream_key = stream.split(":")[-1] if ":" in stream else stream
                if stream_key in self._message_store:
                    self._message_store[stream_key].append(message)
                message_id = str(uuid4())
            
            return RoutingResult(
                success=True,
                signal_ids=[signal.signal_id],
                stream=stream,
                message_ids=[message_id],
            )
            
        except Exception as e:
            logger.error(f"Failed to send to stream {stream}: {e}")
            
            # Send to dead letter
            await self._send_to_dead_letter(signal, str(e))
            
            return RoutingResult(
                success=False,
                signal_ids=[signal.signal_id],
                stream=stream,
                errors=[str(e)],
            )
    
    async def _send_to_dead_letter(
        self,
        signal: LearningSignal,
        error: str,
    ) -> None:
        """Send failed signal to dead letter stream.
        
        Args:
            signal: Failed signal
            error: Error message
        """
        message = {
            "type": "dead_letter",
            "signal_id": signal.signal_id,
            "original_target": signal.target_engine,
            "error": error,
            "correlation_id": signal.correlation_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._message_store["dead_letter"].append(message)
        
        logger.warning(
            f"Signal {signal.signal_id} sent to dead letter: {error}",
            extra={"correlation_id": signal.correlation_id}
        )
    
    def _to_output_format(self, signal: LearningSignal) -> LearningSignalOutput:
        """Convert internal signal to output contract format.
        
        Args:
            signal: Internal LearningSignal
            
        Returns:
            LearningSignalOutput for consumers
        """
        return LearningSignalOutput(
            signal_id=signal.signal_id,
            version=signal.version,
            signal_type=signal.signal_type,
            signal_strength=signal.signal_strength,
            source_feedback_ids=signal.source_feedback_ids,
            recommendation_id=signal.recommendation_id,
            reasoning_trace_id=signal.reasoning_trace_id,
            target_engine=signal.target_engine,
            region_scope=signal.region_scope,
            cross_region_propagation=signal.cross_region_propagation,
            model_id=signal.model_id,
            model_version=signal.model_version,
            model_type=signal.model_type,
            feedback_count=signal.feedback_count,
            average_weight=signal.average_weight,
            confidence_score=signal.confidence_score,
            feedback_window_start=signal.feedback_window_start,
            feedback_window_end=signal.feedback_window_end,
            correlation_id=signal.correlation_id,
            audit_trace_id=signal.audit_trace_id,
            context=signal.context,
            metadata=signal.metadata,
        )
    
    def _get_target_streams(self, target_engine: str) -> List[str]:
        """Get stream names for target engine.
        
        Args:
            target_engine: Target engine name
            
        Returns:
            List of stream names
        """
        if target_engine == "all":
            return [
                settings.STREAM_EVALUATION,
                settings.STREAM_MODEL_ORCHESTRATION,
                settings.STREAM_PIE,
            ]
        elif target_engine == "evaluation":
            return [settings.STREAM_EVALUATION]
        elif target_engine == "model_orchestration":
            return [settings.STREAM_MODEL_ORCHESTRATION]
        elif target_engine == "pie":
            return [settings.STREAM_PIE]
        else:
            logger.warning(f"Unknown target engine: {target_engine}")
            return []
    
    async def get_pending_count(self, stream: Optional[str] = None) -> Dict[str, int]:
        """Get count of pending messages per stream.
        
        Args:
            stream: Optional specific stream
            
        Returns:
            Dict of stream -> count
        """
        if stream:
            stream_key = stream.split(":")[-1] if ":" in stream else stream
            return {stream: len(self._message_store.get(stream_key, []))}
        
        return {k: len(v) for k, v in self._message_store.items()}
    
    async def get_dead_letter_count(self) -> int:
        """Get count of messages in dead letter.
        
        Returns:
            Count of dead letter messages
        """
        return len(self._message_store.get("dead_letter", []))
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics.
        
        Returns:
            Dict with routing stats
        """
        total = len(self._routing_log)
        success = sum(1 for r in self._routing_log if r.success)
        failed = total - success
        
        return {
            "total_routed": total,
            "success_count": success,
            "failed_count": failed,
            "success_rate": success / total if total > 0 else 0.0,
            "pending_by_stream": {
                k: len(v) for k, v in self._message_store.items()
            },
        }
