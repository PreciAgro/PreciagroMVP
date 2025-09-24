"""ARQ worker for executing temporal logic tasks."""
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import traceback
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import ScheduledTask, TaskOutcome, TaskStatus
from ..channels.base import channel_manager
from ..contracts import MessageRequest, OutcomeCreate
from ..telemetry.metrics import engine_metrics
from ..config import config

logger = logging.getLogger(__name__)


class TaskWorker:
    """ARQ worker for executing temporal logic engine tasks."""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.redis_settings = RedisSettings.from_dsn(config.redis_url)

    async def execute_task(self, ctx: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Main task execution function called by ARQ.

        This function is registered with ARQ and receives job data.
        """
        task_id = kwargs.get("task_id")

        if not task_id:
            logger.error("Task execution called without task_id")
            return {"success": False, "error": "Missing task_id"}

        start_time = datetime.utcnow()

        try:
            async with self.db_session_factory() as session:
                # Get task from database
                task = await self._get_task(session, task_id)
                if not task:
                    return {"success": False, "error": f"Task {task_id} not found"}

                # Execute the task based on its type
                result = await self._execute_task_by_type(task, session)

                # Record execution time
                execution_time = (datetime.utcnow() -
                                  start_time).total_seconds()

                # Update task status and record outcome
                await self._finalize_task(task, result, execution_time, session)

                # Record metrics
                engine_metrics.task_executed(
                    task.task_type,
                    task.task_config.get("channel", "unknown"),
                    result["success"],
                    execution_time,
                    task.attempts
                )

                await session.commit()

                logger.info(
                    f"Task {task_id} executed successfully: {result['success']}")
                return result

        except Exception as e:
            logger.error(f"Task {task_id} execution error: {e}")
            logger.debug(traceback.format_exc())

            # Try to mark task as failed in database
            try:
                async with self.db_session_factory() as session:
                    task = await self._get_task(session, task_id)
                    if task:
                        task.status = TaskStatus.FAILED.value
                        task.error_message = str(e)
                        task.completed_at = datetime.utcnow()
                        await session.commit()
            except Exception as db_error:
                logger.error(
                    f"Failed to update task status in database: {db_error}")

            return {"success": False, "error": str(e)}

    async def _get_task(self, session: AsyncSession, task_id: int) -> Optional[ScheduledTask]:
        """Get task from database."""
        stmt = select(ScheduledTask).where(ScheduledTask.id == task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _execute_task_by_type(
        self,
        task: ScheduledTask,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute task based on its type."""
        task_type = task.task_type

        if task_type == "message":
            return await self._execute_message_task(task)
        elif task_type == "webhook":
            return await self._execute_webhook_task(task)
        elif task_type == "schedule":
            return await self._execute_schedule_task(task, session)
        elif task_type == "alert":
            return await self._execute_alert_task(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"success": False, "error": f"Unknown task type: {task_type}"}

    async def _execute_message_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a message sending task."""
        try:
            task_config = task.task_config or {}

            # Extract message details
            recipient = task_config.get("recipient")
            channel = task_config.get("channel", "sms")
            content = task_config.get("message") or task_config.get("content")
            template_id = task_config.get("template_id")
            template_params = task_config.get("template_params", {})
            priority = task_config.get("priority", 5)

            if not recipient:
                return {"success": False, "error": "Missing recipient"}

            # Create message request
            message_request = MessageRequest(
                recipient=recipient,
                channel=channel,
                template_id=template_id,
                content=content,
                template_params=template_params,
                priority=priority
            )

            # Send message through channel
            result = await channel_manager.send_message(channel, message_request)

            return {
                "success": result.success,
                "message_id": result.message_id,
                "status": result.status,
                "error": result.error,
                "metadata": result.metadata
            }

        except Exception as e:
            logger.error(f"Message task execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_webhook_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a webhook task."""
        try:
            import aiohttp

            task_config = task.task_config or {}
            webhook_url = task_config.get("webhook_url")
            webhook_payload = task_config.get("webhook_payload", {})
            method = task_config.get("method", "POST").upper()
            headers = task_config.get(
                "headers", {"Content-Type": "application/json"})
            timeout = task_config.get("timeout", 30)

            if not webhook_url:
                return {"success": False, "error": "Missing webhook_url"}

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                if method == "POST":
                    async with session.post(webhook_url, json=webhook_payload, headers=headers) as response:
                        response_text = await response.text()
                        success = 200 <= response.status < 300

                        return {
                            "success": success,
                            "status_code": response.status,
                            "response": response_text,
                            "error": None if success else f"HTTP {response.status}"
                        }
                elif method == "GET":
                    async with session.get(webhook_url, headers=headers) as response:
                        response_text = await response.text()
                        success = 200 <= response.status < 300

                        return {
                            "success": success,
                            "status_code": response.status,
                            "response": response_text,
                            "error": None if success else f"HTTP {response.status}"
                        }
                else:
                    return {"success": False, "error": f"Unsupported HTTP method: {method}"}

        except Exception as e:
            logger.error(f"Webhook task execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_schedule_task(
        self,
        task: ScheduledTask,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute a scheduling task (create follow-up tasks)."""
        try:
            task_config = task.task_config or {}

            schedule_type = task_config.get("task_type", "message")
            schedule_after = task_config.get(
                "schedule_after", 3600)  # 1 hour default
            params = task_config.get("params", {})

            # Create new scheduled task
            new_task = ScheduledTask(
                rule_id=task.rule_id,
                triggering_event_id=task.triggering_event_id,
                task_type=schedule_type,
                task_config=params,
                scheduled_for=datetime.utcnow() + timedelta(seconds=schedule_after),
                max_attempts=3
            )

            session.add(new_task)
            await session.flush()

            return {
                "success": True,
                "scheduled_task_id": new_task.id,
                "scheduled_for": new_task.scheduled_for.isoformat()
            }

        except Exception as e:
            logger.error(f"Schedule task execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_alert_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute an alert task (high priority notification)."""
        try:
            task_config = task.task_config or {}

            # Alert tasks are essentially high-priority messages
            alert_config = task_config.copy()
            alert_config["priority"] = 9  # Force high priority

            # Update task config and execute as message
            task.task_config = alert_config

            return await self._execute_message_task(task)

        except Exception as e:
            logger.error(f"Alert task execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _finalize_task(
        self,
        task: ScheduledTask,
        result: Dict[str, Any],
        execution_time: float,
        session: AsyncSession
    ):
        """Update task status and record outcome."""
        # Update task
        if result["success"]:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()
            task.result = result
            task.error_message = None
        else:
            if task.attempts < task.max_attempts:
                # Task will be retried
                task.status = TaskStatus.PENDING.value
                task.scheduled_for = datetime.utcnow() + timedelta(seconds=300)  # Retry in 5 minutes
            else:
                # Max attempts reached
                task.status = TaskStatus.FAILED.value
                task.completed_at = datetime.utcnow()
                task.error_message = result.get("error")

            task.result = result

        # Record outcome
        outcome = TaskOutcome(
            task_id=task.id,
            outcome_type="success" if result["success"] else "failure",
            outcome_data=result,
            source="task_worker"
        )

        session.add(outcome)

    async def startup(self, ctx: Dict[str, Any]):
        """Worker startup function."""
        logger.info("Temporal logic task worker starting up")

        # Initialize database connections, channels, etc.
        # This is called once when the worker starts

        # Register channels if not already registered
        from ..channels.whatsapp_meta import WhatsAppMetaChannel
        from ..channels.sms_twilio import TwilioSMSChannel

        try:
            if not channel_manager.get_channel("whatsapp"):
                whatsapp_channel = WhatsAppMetaChannel()
                channel_manager.register_channel(whatsapp_channel)

            if not channel_manager.get_channel("sms"):
                sms_channel = TwilioSMSChannel()
                channel_manager.register_channel(sms_channel)

        except Exception as e:
            logger.warning(f"Could not initialize some channels: {e}")

    async def shutdown(self, ctx: Dict[str, Any]):
        """Worker shutdown function."""
        logger.info("Temporal logic task worker shutting down")

    def get_arq_functions(self):
        """Get functions to register with ARQ."""
        return [
            {
                "function": self.execute_task,
                "name": "execute_task"
            }
        ]

    def get_arq_settings(self):
        """Get ARQ worker settings."""
        return {
            "functions": [self.execute_task],
            "on_startup": self.startup,
            "on_shutdown": self.shutdown,
            "redis_settings": self.redis_settings,
            "job_timeout": config.arq_job_timeout,
            "max_jobs": config.arq_max_jobs,
            "retry_jobs": config.arq_retry_jobs,
            "max_tries": config.arq_max_tries,
            "queue_name": "temporal_engine_tasks"
        }


async def create_worker_pool(db_session_factory):
    """Create ARQ worker pool."""
    worker = TaskWorker(db_session_factory)

    pool = await create_pool(worker.redis_settings)

    return pool, worker


# Standalone function for ARQ to discover
async def execute_task(ctx, **kwargs):
    """Standalone task execution function for ARQ."""
    # This will be replaced by the worker instance method
    # when the worker is properly initialized
    logger.error("Task execution called but worker not properly initialized")
    return {"success": False, "error": "Worker not initialized"}


# Worker configuration for direct ARQ usage
class WorkerSettings:
    """ARQ worker settings."""

    functions = [execute_task]
    redis_settings = RedisSettings.from_dsn(config.redis_url)
    job_timeout = config.arq_job_timeout
    max_jobs = config.arq_max_jobs
    retry_jobs = config.arq_retry_jobs
    max_tries = config.arq_max_tries
