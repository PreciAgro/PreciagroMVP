"""Feedback Pipeline - Celery tasks for async feedback processing.

Tasks in this module handle the full feedback processing pipeline:
1. process_feedback_event - Complete pipeline for a single event
2. generate_learning_signals - Generate signals from weighted feedback
3. route_to_consumers - Route signals to downstream engines
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .celery_app import celery_app
from ..services.capture_service import CaptureService
from ..services.validation_service import ValidationService
from ..services.weighting_service import WeightingService
from ..services.signal_service import SignalService
from ..services.routing_service import RoutingService
from ..services.audit_service import AuditService
from ..contracts.upstream import FarmerProfileContext, RecommendationContext, OutcomeTimingContext
from ..config import settings

logger = logging.getLogger(__name__)

# Service instances for tasks
capture_service = CaptureService()
validation_service = ValidationService()
weighting_service = WeightingService()
signal_service = SignalService()
routing_service = RoutingService()
audit_service = AuditService()


@celery_app.task(bind=True, max_retries=3, queue="fle.default")
def process_feedback_event(
    self,
    feedback_id: str,
    farmer_profile: Optional[Dict[str, Any]] = None,
    recommendation_context: Optional[Dict[str, Any]] = None,
    timing_context: Optional[Dict[str, Any]] = None,
):
    """Process a feedback event through the full pipeline.
    
    Pipeline stages:
    1. Retrieve feedback event
    2. Create audit trace
    3. Validate (duplicate, contradiction, noise detection)
    4. Compute weight
    5. Generate learning signal
    6. Route to consumers
    7. Complete audit trace
    
    Args:
        feedback_id: ID of the feedback event to process
        farmer_profile: Optional farmer profile context
        recommendation_context: Optional recommendation context
        timing_context: Optional timing context
        
    Returns:
        Dict with processing results
    """
    import asyncio
    
    async def _process():
        try:
            # 1. Get event
            event = await capture_service.get_event(feedback_id)
            if not event:
                logger.error(f"Feedback {feedback_id} not found")
                return {"success": False, "error": "Feedback not found"}
            
            # 2. Create audit trace
            trace = await audit_service.create_trace(event)
            
            # 3. Get existing events for recommendation
            existing = await capture_service.get_events_for_recommendation(
                event.recommendation_id
            )
            
            # Parse contexts
            farmer_ctx = (
                FarmerProfileContext(**farmer_profile) if farmer_profile else None
            )
            rec_ctx = (
                RecommendationContext(**recommendation_context)
                if recommendation_context else None
            )
            timing_ctx = (
                OutcomeTimingContext(**timing_context) if timing_context else None
            )
            
            # 4. Validate
            validation_result = await validation_service.validate(
                event, existing, farmer_ctx
            )
            
            await audit_service.add_validation_step(
                trace.trace_id,
                validation_result.is_valid,
                {
                    "is_duplicate": validation_result.is_duplicate,
                    "is_contradiction": validation_result.is_contradiction,
                    "is_noise": validation_result.is_noise,
                }
            )
            
            if not validation_result.is_valid:
                await audit_service.complete_trace(
                    trace.trace_id,
                    status="error",
                    error_message="Validation failed"
                )
                return {
                    "success": False,
                    "feedback_id": feedback_id,
                    "error": "Validation failed",
                    "validation_errors": validation_result.errors,
                }
            
            # 5. Weight
            weighted = await weighting_service.compute_weight(
                event=event,
                farmer_profile=farmer_ctx,
                recommendation_context=rec_ctx,
                timing_context=timing_ctx,
                validation_flags={
                    "is_duplicate": validation_result.is_duplicate,
                    "is_contradiction": validation_result.is_contradiction,
                    "is_noise": validation_result.is_noise,
                    "duplicate_of_id": validation_result.duplicate_of_id,
                    "contradiction_ids": validation_result.contradiction_ids,
                    "noise_reason": validation_result.noise_reason,
                }
            )
            
            await audit_service.add_weighting_step(trace.trace_id, weighted)
            
            # Check if flagged
            if weighted.is_flagged:
                await audit_service.add_flagging_step(
                    trace.trace_id,
                    weighted.weighted_id,
                    weighted.flag_reasons,
                )
            
            # 6. Generate signal
            signal = await signal_service.generate_signal(
                weighted,
                recommendation_context=rec_ctx,
                target_engine="all",
            )
            
            await audit_service.add_signal_step(trace.trace_id, signal)
            
            # 7. Route
            result = await routing_service.route_signal(signal)
            
            await audit_service.add_routing_step(
                trace.trace_id,
                signal.signal_id,
                result.stream,
                result.success,
                result.errors[0] if result.errors else None,
            )
            
            # Mark routed
            if result.success:
                await signal_service.mark_routed([signal.signal_id], result.stream)
            
            # 8. Complete trace
            await audit_service.complete_trace(
                trace.trace_id,
                status="flagged" if weighted.is_flagged else "completed"
            )
            
            logger.info(f"Processed feedback {feedback_id} successfully")
            
            return {
                "success": True,
                "feedback_id": feedback_id,
                "weighted_id": weighted.weighted_id,
                "signal_id": signal.signal_id,
                "is_flagged": weighted.is_flagged,
                "final_weight": weighted.final_weight,
            }
            
        except Exception as e:
            logger.error(f"Failed to process feedback {feedback_id}: {e}")
            raise self.retry(exc=e, countdown=60)
    
    # Run async function
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_process())
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, queue="fle.batch")
def generate_learning_signals(
    self,
    recommendation_id: str,
    target_engine: str = "all",
):
    """Generate aggregated learning signal for a recommendation.
    
    Aggregates all weighted feedback for a recommendation
    into a single learning signal.
    
    Args:
        recommendation_id: ID of the recommendation
        target_engine: Target engine for the signal
        
    Returns:
        Dict with signal generation results
    """
    import asyncio
    
    async def _generate():
        try:
            # Get all weighted feedback for recommendation
            weighted_items = await weighting_service.get_weighted_for_recommendation(
                recommendation_id
            )
            
            if not weighted_items:
                return {
                    "success": False,
                    "recommendation_id": recommendation_id,
                    "error": "No weighted feedback found",
                }
            
            # Generate aggregated signal
            signal = await signal_service.generate_aggregated_signal(
                weighted_items,
                target_engine=target_engine,
            )
            
            logger.info(
                f"Generated aggregated signal for {recommendation_id} "
                f"from {len(weighted_items)} items"
            )
            
            return {
                "success": True,
                "recommendation_id": recommendation_id,
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type.value,
                "signal_strength": signal.signal_strength,
                "feedback_count": signal.feedback_count,
            }
            
        except Exception as e:
            logger.error(f"Failed to generate signal for {recommendation_id}: {e}")
            raise self.retry(exc=e, countdown=30)
    
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, queue="fle.priority")
def route_to_consumers(
    self,
    signal_ids: list[str],
):
    """Route signals to downstream consumers.
    
    Args:
        signal_ids: List of signal IDs to route
        
    Returns:
        Dict with routing results
    """
    import asyncio
    
    async def _route():
        try:
            signals = []
            for signal_id in signal_ids:
                signal = await signal_service.get_signal(signal_id)
                if signal and not signal.is_routed:
                    signals.append(signal)
            
            if not signals:
                return {
                    "success": True,
                    "routed_count": 0,
                    "message": "No unrouted signals found",
                }
            
            # Route batch
            result = await routing_service.route_batch(signals)
            
            # Mark as routed
            if result.success:
                await signal_service.mark_routed(signal_ids, result.stream)
            
            return {
                "success": result.success,
                "routed_count": len(signals),
                "stream": result.stream,
                "errors": result.errors,
            }
            
        except Exception as e:
            logger.error(f"Failed to route signals: {e}")
            raise self.retry(exc=e, countdown=30)
    
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_route())
    finally:
        loop.close()


@celery_app.task(queue="fle.batch")
def route_pending_signals():
    """Periodic task to route any pending signals.
    
    Runs on schedule to catch any unrouted signals.
    """
    import asyncio
    
    async def _route_pending():
        try:
            # Get unrouted signals for each engine
            for engine in ["evaluation", "model_orchestration", "pie"]:
                signals = await signal_service.get_signals_for_engine(
                    engine=engine,
                    limit=settings.SIGNAL_BATCH_SIZE,
                )
                
                if signals:
                    result = await routing_service.route_batch(signals)
                    if result.success:
                        await signal_service.mark_routed(
                            [s.signal_id for s in signals],
                            result.stream,
                        )
                    logger.info(f"Routed {len(signals)} pending signals to {engine}")
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to route pending signals: {e}")
            return {"success": False, "error": str(e)}
    
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_route_pending())
    finally:
        loop.close()


@celery_app.task(queue="fle.batch")
def cleanup_old_events():
    """Periodic task to cleanup old processed events.
    
    Note: This only cleans up processed data that has been
    successfully routed. Raw FeedbackEvents are never deleted
    (append-only policy).
    """
    logger.info("Cleanup task ran - FeedbackEvents are append-only, no cleanup needed")
    return {"success": True, "message": "Append-only policy - no cleanup performed"}
