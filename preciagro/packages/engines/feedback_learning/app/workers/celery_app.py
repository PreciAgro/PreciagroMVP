"""Celery application configuration for FLE.

Celery handles async processing of feedback through the pipeline:
1. Capture -> 2. Validate -> 3. Weight -> 4. Signal -> 5. Route

Uses Redis as broker and result backend.
"""

from celery import Celery

from ..config import settings

# Create Celery app
celery_app = Celery(
    "fle_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["preciagro.packages.engines.feedback_learning.app.workers.feedback_pipeline"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,  # Ack after task completes for reliability
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minute hard limit
    task_soft_time_limit=240,  # 4 minute soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time for ordering
    worker_concurrency=4,  # 4 concurrent workers
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute retry delay
    task_max_retries=3,
    
    # Queue settings
    task_default_queue="fle.default",
    task_queues={
        "fle.default": {"routing_key": "fle.default"},
        "fle.priority": {"routing_key": "fle.priority"},
        "fle.batch": {"routing_key": "fle.batch"},
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "process-pending-signals": {
            "task": "preciagro.packages.engines.feedback_learning.app.workers.feedback_pipeline.route_pending_signals",
            "schedule": 60.0,  # Every 60 seconds
        },
        "cleanup-old-events": {
            "task": "preciagro.packages.engines.feedback_learning.app.workers.feedback_pipeline.cleanup_old_events",
            "schedule": 3600.0,  # Every hour
        },
    },
)


# Error handling
@celery_app.task(bind=True, max_retries=3)
def handle_task_failure(self, exc, task_id, args, kwargs, einfo):
    """Handle task failures.
    
    Logs error and sends to dead letter if max retries exceeded.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.error(
        f"Task {task_id} failed: {exc}",
        extra={
            "task_id": task_id,
            "args": args,
            "kwargs": kwargs,
            "traceback": str(einfo),
        }
    )
