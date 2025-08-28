"""Dispatcher for selecting and enqueueing due jobs."""
import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from ..models import ScheduledTask, TaskStatus
from ..policies.quiet_hours import apply_quiet_hours_policy
from ..policies.rate_limits import apply_rate_limiting
from ..telemetry.metrics import engine_metrics
from ..config import config

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """Dispatches due tasks to the worker queue."""
    
    def __init__(self, redis_pool, db_session_factory):
        self.redis_pool = redis_pool
        self.db_session_factory = db_session_factory
        self.queue_name = "temporal_engine_tasks"
        self.is_running = False
        self.dispatch_interval = 30  # seconds
    
    async def start_dispatcher(self):
        """Start the task dispatcher loop."""
        self.is_running = True
        logger.info("Task dispatcher started")
        
        try:
            while self.is_running:
                await self._dispatch_due_tasks()
                await asyncio.sleep(self.dispatch_interval)
        except Exception as e:
            logger.error(f"Task dispatcher error: {e}")
        finally:
            logger.info("Task dispatcher stopped")
    
    async def stop_dispatcher(self):
        """Stop the task dispatcher."""
        self.is_running = False
    
    async def _dispatch_due_tasks(self):
        """Find and dispatch tasks that are due for execution."""
        try:
            async with self.db_session_factory() as session:
                # Find tasks due for execution
                due_tasks = await self._get_due_tasks(session)
                
                if not due_tasks:
                    logger.debug("No due tasks found")
                    return
                
                logger.info(f"Found {len(due_tasks)} due tasks")
                
                # Group tasks by priority
                high_priority_tasks = [t for t in due_tasks if t.task_config.get("priority", 5) >= 8]
                normal_priority_tasks = [t for t in due_tasks if t.task_config.get("priority", 5) < 8]
                
                # Dispatch high priority first
                for task in high_priority_tasks:
                    await self._dispatch_single_task(task, session, high_priority=True)
                
                for task in normal_priority_tasks:
                    await self._dispatch_single_task(task, session, high_priority=False)
                
                await session.commit()
        
        except Exception as e:
            logger.error(f"Error dispatching due tasks: {e}")
    
    async def _get_due_tasks(self, session: AsyncSession) -> List[ScheduledTask]:
        """Get tasks that are due for execution."""
        current_time = datetime.utcnow()
        
        # Query for tasks that are:
        # 1. Due for execution (scheduled_for <= now)
        # 2. In pending status
        # 3. Haven't exceeded max attempts
        stmt = select(ScheduledTask).where(
            and_(
                ScheduledTask.scheduled_for <= current_time,
                ScheduledTask.status == TaskStatus.PENDING.value,
                ScheduledTask.attempts < ScheduledTask.max_attempts
            )
        ).order_by(
            ScheduledTask.scheduled_for.asc()
        ).limit(100)  # Process max 100 tasks per cycle
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def _dispatch_single_task(
        self, 
        task: ScheduledTask, 
        session: AsyncSession, 
        high_priority: bool = False
    ):
        """Dispatch a single task to the worker queue."""
        try:
            # Apply policies
            adjusted_time, policy_reason = await self._apply_policies(task)
            
            # If task needs to be delayed, reschedule it
            if adjusted_time > datetime.utcnow():
                await self._reschedule_task(task, adjusted_time, policy_reason, session)
                return
            
            # Mark task as running
            task.status = TaskStatus.RUNNING.value
            task.attempts += 1
            task.executed_at = datetime.utcnow()
            
            # Create job payload
            job_payload = {
                "task_id": task.id,
                "task_type": task.task_type,
                "task_config": task.task_config,
                "rule_id": task.rule_id,
                "attempt": task.attempts,
                "max_attempts": task.max_attempts,
                "high_priority": high_priority
            }
            
            # Enqueue job
            queue_name = f"{self.queue_name}:high" if high_priority else self.queue_name
            await self._enqueue_job(queue_name, job_payload)
            
            # Record metrics
            engine_metrics.task_scheduled(
                task.task_type,
                task.task_config.get("channel", "unknown"),
                0  # No additional delay since it's being dispatched now
            )
            
            logger.info(f"Dispatched task {task.id} (type: {task.task_type}, attempt: {task.attempts})")
        
        except Exception as e:
            logger.error(f"Error dispatching task {task.id}: {e}")
            # Mark task as failed
            await self._mark_task_failed(task, str(e), session)
    
    async def _apply_policies(self, task: ScheduledTask) -> tuple[datetime, str]:
        """Apply quiet hours and rate limiting policies to a task."""
        scheduled_time = datetime.utcnow()
        
        # Extract task details
        task_config = task.task_config or {}
        channel = task_config.get("channel", "unknown")
        message_type = task.task_type
        priority = task_config.get("priority", 5)
        user_id = task_config.get("recipient", "unknown")
        
        # Apply quiet hours policy
        adjusted_time, quiet_hours_reason = apply_quiet_hours_policy(
            channel, scheduled_time, message_type, priority
        )
        
        # Apply rate limiting
        final_time, rate_limit_reason = apply_rate_limiting(
            user_id, channel, adjusted_time, priority
        )
        
        # Combine reasons
        policy_reasons = []
        if quiet_hours_reason != "Outside quiet hours":
            policy_reasons.append(f"Quiet hours: {quiet_hours_reason}")
        if rate_limit_reason != "Within rate limits":
            policy_reasons.append(f"Rate limit: {rate_limit_reason}")
        
        combined_reason = "; ".join(policy_reasons) if policy_reasons else "No policy delays"
        
        return final_time, combined_reason
    
    async def _reschedule_task(
        self, 
        task: ScheduledTask, 
        new_time: datetime, 
        reason: str, 
        session: AsyncSession
    ):
        """Reschedule a task due to policy constraints."""
        task.scheduled_for = new_time
        
        delay_seconds = int((new_time - datetime.utcnow()).total_seconds())
        
        logger.info(f"Rescheduled task {task.id} by {delay_seconds} seconds: {reason}")
        
        # Record metrics for policy applications
        if "quiet hours" in reason.lower():
            engine_metrics.quiet_hours_applied(
                task.task_config.get("channel", "unknown"),
                delay_seconds
            )
        
        if "rate limit" in reason.lower():
            engine_metrics.rate_limit_applied(
                "unknown",  # We don't have the limit type here
                task.task_config.get("recipient", "unknown"),
                delay_seconds
            )
    
    async def _enqueue_job(self, queue_name: str, job_payload: Dict[str, Any]):
        """Enqueue job in Redis for ARQ workers."""
        import json
        import uuid
        
        job_id = str(uuid.uuid4())
        
        # ARQ job format
        arq_job = {
            "job_id": job_id,
            "function": "execute_task",
            "args": [],
            "kwargs": job_payload,
            "job_try": 1,
            "enqueue_time": datetime.utcnow().isoformat(),
            "timeout": config.arq_job_timeout
        }
        
        # Push to Redis queue
        async with self.redis_pool.get() as redis:
            await redis.lpush(queue_name, json.dumps(arq_job))
        
        logger.debug(f"Enqueued job {job_id} to queue {queue_name}")
    
    async def _mark_task_failed(self, task: ScheduledTask, error: str, session: AsyncSession):
        """Mark a task as failed."""
        task.status = TaskStatus.FAILED.value
        task.error_message = error
        task.completed_at = datetime.utcnow()
        
        logger.error(f"Marked task {task.id} as failed: {error}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the task queues."""
        try:
            async with self.redis_pool.get() as redis:
                normal_queue_len = await redis.llen(self.queue_name)
                high_priority_queue_len = await redis.llen(f"{self.queue_name}:high")
                
                return {
                    "normal_queue_length": normal_queue_len,
                    "high_priority_queue_length": high_priority_queue_len,
                    "total_queued": normal_queue_len + high_priority_queue_len,
                    "dispatcher_running": self.is_running
                }
        
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {
                "error": str(e),
                "dispatcher_running": self.is_running
            }
    
    async def get_due_tasks_count(self) -> int:
        """Get count of tasks due for execution."""
        try:
            async with self.db_session_factory() as session:
                current_time = datetime.utcnow()
                
                stmt = select(ScheduledTask).where(
                    and_(
                        ScheduledTask.scheduled_for <= current_time,
                        ScheduledTask.status == TaskStatus.PENDING.value,
                        ScheduledTask.attempts < ScheduledTask.max_attempts
                    )
                )
                
                result = await session.execute(stmt)
                tasks = result.scalars().all()
                return len(tasks)
        
        except Exception as e:
            logger.error(f"Error getting due tasks count: {e}")
            return 0
    
    async def reschedule_failed_tasks(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Reschedule failed tasks that might be retryable."""
        try:
            async with self.db_session_factory() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
                
                # Find failed tasks that are recent and haven't exceeded max attempts
                stmt = select(ScheduledTask).where(
                    and_(
                        ScheduledTask.status == TaskStatus.FAILED.value,
                        ScheduledTask.completed_at >= cutoff_time,
                        ScheduledTask.attempts < ScheduledTask.max_attempts
                    )
                )
                
                result = await session.execute(stmt)
                failed_tasks = result.scalars().all()
                
                rescheduled_count = 0
                
                for task in failed_tasks:
                    # Check if error is retryable
                    if self._is_retryable_error(task.error_message):
                        # Reset task for retry
                        task.status = TaskStatus.PENDING.value
                        task.scheduled_for = datetime.utcnow() + timedelta(minutes=5)  # Retry in 5 minutes
                        task.error_message = None
                        rescheduled_count += 1
                
                await session.commit()
                
                logger.info(f"Rescheduled {rescheduled_count} failed tasks for retry")
                
                return {
                    "total_failed_tasks": len(failed_tasks),
                    "rescheduled_tasks": rescheduled_count
                }
        
        except Exception as e:
            logger.error(f"Error rescheduling failed tasks: {e}")
            return {"error": str(e)}
    
    def _is_retryable_error(self, error_message: Optional[str]) -> bool:
        """Check if an error is retryable."""
        if not error_message:
            return False
        
        error_lower = error_message.lower()
        
        # Non-retryable errors
        non_retryable = [
            "invalid phone number",
            "unauthorized",
            "forbidden",
            "not found",
            "bad request",
            "invalid template",
            "permission denied"
        ]
        
        for non_retryable_error in non_retryable:
            if non_retryable_error in error_lower:
                return False
        
        # Retryable errors
        retryable = [
            "timeout",
            "connection",
            "network",
            "server error",
            "service unavailable",
            "rate limit"
        ]
        
        for retryable_error in retryable:
            if retryable_error in error_lower:
                return True
        
        # Default to retryable for unknown errors
        return True


class PriorityTaskDispatcher(TaskDispatcher):
    """Enhanced dispatcher with priority-based scheduling."""
    
    async def _dispatch_due_tasks(self):
        """Dispatch tasks with priority-based ordering."""
        try:
            async with self.db_session_factory() as session:
                # Get tasks grouped by priority
                priority_groups = await self._get_tasks_by_priority(session)
                
                total_dispatched = 0
                
                # Process highest priority first
                for priority_level in sorted(priority_groups.keys(), reverse=True):
                    tasks = priority_groups[priority_level]
                    
                    for task in tasks:
                        await self._dispatch_single_task(
                            task, 
                            session, 
                            high_priority=(priority_level >= 8)
                        )
                        total_dispatched += 1
                
                if total_dispatched > 0:
                    logger.info(f"Dispatched {total_dispatched} tasks across priority levels")
                
                await session.commit()
        
        except Exception as e:
            logger.error(f"Error in priority-based dispatch: {e}")
    
    async def _get_tasks_by_priority(self, session: AsyncSession) -> Dict[int, List[ScheduledTask]]:
        """Get tasks grouped by priority level."""
        current_time = datetime.utcnow()
        
        stmt = select(ScheduledTask).where(
            and_(
                ScheduledTask.scheduled_for <= current_time,
                ScheduledTask.status == TaskStatus.PENDING.value,
                ScheduledTask.attempts < ScheduledTask.max_attempts
            )
        ).order_by(
            ScheduledTask.scheduled_for.asc()
        ).limit(100)
        
        result = await session.execute(stmt)
        all_tasks = result.scalars().all()
        
        # Group by priority
        priority_groups = {}
        
        for task in all_tasks:
            priority = task.task_config.get("priority", 5) if task.task_config else 5
            
            if priority not in priority_groups:
                priority_groups[priority] = []
            
            priority_groups[priority].append(task)
        
        return priority_groups
