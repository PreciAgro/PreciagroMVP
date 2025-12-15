"""Telemetry and metrics for temporal logic engine."""

from datetime import datetime, timezone
from typing import Any, Dict

from prometheus_client import Counter, Histogram

# Notification metrics
send_attempts = Counter("notif_send_attempts", "send attempts", ["channel"])
send_results = Counter("notif_send_results", "send results", ["channel", "result"])
send_latency = Histogram("notif_send_latency_seconds", "send latency", ["channel"])

# Engine metrics (aliases for backwards compatibility)
notification_attempts = send_attempts
notification_results = send_results
notification_latency = send_latency

# Event processing metrics
events_processed = Counter("temporal_events_processed", "events processed", ["event_type"])
tasks_created = Counter("temporal_tasks_created", "tasks created", ["rule_id"])


class EngineMetrics:
    """Lightweight facade providing structured access to Prometheus counters."""

    def __init__(self) -> None:
        self._system_snapshot: Dict[str, float] = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
        }
        self._business_snapshot: Dict[str, Dict[str, int]] = {
            "events": {},
            "tasks": {},
            "messages": {},
        }

    def get_system_metrics(self) -> dict:
        """Return cached metrics for test assertions."""
        return self._system_snapshot

    def get_current_timestamp(self) -> float:
        """Get current timestamp as a float (seconds since epoch)."""
        return datetime.now(timezone.utc).timestamp()

    def get_business_metrics(self) -> dict:
        """Return aggregated business metrics."""
        return self._business_snapshot

    def event_processed(self, event_type: str, result: str) -> None:
        """Record an event processing outcome."""
        events_processed.labels(event_type=event_type).inc()
        event_counter = self._business_snapshot["events"].setdefault(event_type, 0)
        self._business_snapshot["events"][event_type] = event_counter + 1

    def task_executed(
        self,
        task_type: str,
        channel: str = "unknown",
        success: Any = True,
        execution_time: float = 0.0,
        attempts: int = 0,
    ) -> None:
        """Record task execution metrics."""
        send_attempts.labels(channel=channel).inc()
        status = "success"
        success_flag = success
        if isinstance(success, str):
            status = success
            success_flag = success.lower() in {"success", "completed", "done"}
        else:
            status = "success" if success else "failure"
        success_bool = bool(success_flag)
        send_results.labels(channel=channel, result=status).inc()
        send_latency.labels(channel=channel).observe(max(execution_time, 0.0))
        task_counter = self._business_snapshot["tasks"].setdefault(task_type, 0)
        self._business_snapshot["tasks"][task_type] = task_counter + 1
        if not success_bool:
            message_counter = self._business_snapshot["messages"].setdefault(channel, 0)
            self._business_snapshot["messages"][channel] = message_counter + 1

    def message_sent(self, channel: str, status: str) -> None:
        """Record message results."""
        send_results.labels(channel=channel, result=status).inc()

    def system_startup(self) -> None:
        """Record system startup event."""
        pass

    def get_performance_metrics(self) -> dict:
        """Return performance metrics."""
        return {
            "cpu_usage": self._system_snapshot["cpu_usage"],
            "memory_usage": self._system_snapshot["memory_usage"],
        }

    def request_started(self, method: str, endpoint: str) -> None:
        """Record request start."""
        pass

    def request_completed(
        self, method: str, endpoint: str, status_code: int, duration: float
    ) -> None:
        """Record request completion."""
        pass

    def request_failed(self, method: str, endpoint: str, error: str) -> None:
        """Record request failure."""
        pass

    def task_scheduled(self, task_type: str, channel: str, delay_seconds: float) -> None:
        """Compatibility shim for dispatcher metrics."""
        tasks_created.labels(rule_id=task_type).inc()
        task_counter = self._business_snapshot["tasks"].setdefault(task_type, 0)
        self._business_snapshot["tasks"][task_type] = task_counter + 1

    def quiet_hours_applied(self, channel: str, delay_seconds: int) -> None:
        """Record quiet hour adjustments (no-op for now)."""
        _ = (channel, delay_seconds)


engine_metrics = EngineMetrics()
