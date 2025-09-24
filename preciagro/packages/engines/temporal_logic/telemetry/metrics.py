"""Telemetry and metrics for temporal logic engine."""
from prometheus_client import Counter, Histogram

# Notification metrics
send_attempts = Counter("notif_send_attempts", "send attempts", ["channel"])
send_results = Counter("notif_send_results",
                       "send results", ["channel", "result"])
send_latency = Histogram("notif_send_latency_seconds",
                         "send latency", ["channel"])

# Engine metrics (aliases for backwards compatibility)
notification_attempts = send_attempts
notification_results = send_results
notification_latency = send_latency

# Event processing metrics
events_processed = Counter("temporal_events_processed",
                           "events processed", ["event_type"])
tasks_created = Counter("temporal_tasks_created", "tasks created", ["rule_id"])
