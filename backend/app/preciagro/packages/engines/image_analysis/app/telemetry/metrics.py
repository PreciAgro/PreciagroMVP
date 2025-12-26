"""Prometheus metrics for the Image Analysis Engine."""

from __future__ import annotations

from prometheus_client import Counter, Histogram


class TelemetryRecorder:
    def __init__(self) -> None:
        self.latency = Histogram(
            "image_analysis_latency_seconds",
            "Latency for single image analysis requests",
            buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 5.0),
            labelnames=("status",),
        )
        self.quality_failures = Counter(
            "image_analysis_quality_failures_total",
            "Number of requests failing the quality gate",
        )
        self.uncertain_counter = Counter(
            "image_analysis_uncertain_total",
            "Number of responses marked uncertain",
        )

    def record_latency(self, latency_ms: float, status: str) -> None:
        self.latency.labels(status=status).observe(latency_ms / 1000.0)

    def record_quality_failure(self) -> None:
        self.quality_failures.inc()

    def record_uncertain(self) -> None:
        self.uncertain_counter.inc()


telemetry = TelemetryRecorder()
