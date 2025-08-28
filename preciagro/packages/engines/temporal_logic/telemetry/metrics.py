"""Telemetry and metrics for temporal logic engine."""
from prometheus_client import Counter, Histogram

send_attempts = Counter("notif_send_attempts", "send attempts", ["channel"])
send_results = Counter("notif_send_results", "send results", ["channel", "result"])
send_latency = Histogram("notif_send_latency_seconds", "send latency", ["channel"])
