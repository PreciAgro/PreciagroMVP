"""Telemetry and metrics for Geo Context Engine."""

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional

from prometheus_client import Counter, Gauge, Histogram

# Metrics definitions
REQUEST_COUNT = Counter(
    "geo_context_requests_total",
    "Total number of geo context requests",
    ["endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "geo_context_request_duration_seconds", "Request duration in seconds", ["endpoint"]
)

CACHE_OPERATIONS = Counter(
    "geo_context_cache_operations_total",
    "Cache operations",
    ["operation", "result"],  # hit, miss, set, delete
)

DATA_SOURCES_USED = Counter(
    "geo_context_data_sources_total",
    "Data sources used for resolving context",
    ["source_type"],  # spatial, soil, climate, calendar
)

ACTIVE_CONNECTIONS = Gauge("geo_context_db_connections_active", "Active database connections")

ACTIVE_REQUESTS = Gauge("geo_context_active_requests", "Number of active geocontext requests")

RESOLVER_DURATION = Histogram(
    "geo_context_resolver_duration_seconds",
    "Individual resolver duration in seconds",
    ["resolver_type"],  # spatial, soil, climate, calendar
)

API_ERRORS = Counter("geo_context_errors_total", "Total API errors", ["error_type", "endpoint"])


class MetricsCollector:
    """Metrics collection utilities."""

    @staticmethod
    def record_request(endpoint: str, status: str):
        """Record API request."""
        REQUEST_COUNT.labels(endpoint=endpoint, status=status).inc()

    @staticmethod
    def time_request(endpoint: str):
        """Context manager for timing requests."""
        return REQUEST_DURATION.labels(endpoint=endpoint).time()

    @staticmethod
    def record_cache_operation(operation: str, result: str):
        """Record cache operation."""
        CACHE_OPERATIONS.labels(operation=operation, result=result).inc()

    @staticmethod
    def record_data_source_usage(source_type: str):
        """Record data source usage."""
        DATA_SOURCES_USED.labels(source_type=source_type).inc()

    @staticmethod
    def set_active_connections(count: int):
        """Set active database connections count."""
        ACTIVE_CONNECTIONS.set(count)

    @staticmethod
    def time_resolver(resolver_type: str):
        """Context manager for timing individual resolvers."""
        return RESOLVER_DURATION.labels(resolver_type=resolver_type).time()

    @staticmethod
    def record_error(error_type: str, endpoint: str):
        """Record API error."""
        API_ERRORS.labels(error_type=error_type, endpoint=endpoint).inc()


class PerformanceTracker:
    """Track performance metrics during request processing."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = time.time()
        self.resolver_times: Dict[str, float] = {}
        self.data_sources: set = set()

    def start_resolver(self, resolver_type: str) -> "ResolverTimer":
        """Start timing a resolver."""
        return ResolverTimer(self, resolver_type)

    def record_data_source(self, source: str):
        """Record that a data source was used."""
        self.data_sources.add(source)
        MetricsCollector.record_data_source_usage(source)

    def get_total_time(self) -> float:
        """Get total request time."""
        return time.time() - self.start_time

    def get_metrics_summary(self) -> Dict:
        """Get summary of performance metrics."""
        return {
            "request_id": self.request_id,
            "total_time_ms": self.get_total_time() * 1000,
            "resolver_times_ms": {k: v * 1000 for k, v in self.resolver_times.items()},
            "data_sources_used": list(self.data_sources),
        }


class ResolverTimer:
    """Context manager for timing individual resolvers."""

    def __init__(self, tracker: PerformanceTracker, resolver_type: str):
        self.tracker = tracker
        self.resolver_type = resolver_type
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.tracker.resolver_times[self.resolver_type] = duration

        # Record in Prometheus metrics
        RESOLVER_DURATION.labels(resolver_type=self.resolver_type).observe(duration)


def get_health_metrics() -> Dict:
    """Get health metrics for monitoring."""
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "metrics": {
            "total_requests": REQUEST_COUNT._value.sum(),
            "active_connections": ACTIVE_CONNECTIONS._value.get(),
            "cache_hit_rate": _calculate_cache_hit_rate(),
            "average_response_time": _get_average_response_time(),
        },
    }


def _calculate_cache_hit_rate() -> Optional[float]:
    """Calculate cache hit rate."""
    try:
        hits = CACHE_OPERATIONS.labels(operation="get", result="hit")._value.get()
        misses = CACHE_OPERATIONS.labels(operation="get", result="miss")._value.get()
        total = hits + misses
        return hits / total if total > 0 else None
    except (
        Exception
    ):  # FIX: Ruff E722 lint - use explicit exception to avoid masking SystemExit/KeyboardInterrupt.
        return None


def _get_average_response_time() -> Optional[float]:
    """Get average response time."""
    try:
        # This is a simplified calculation - in production you'd use proper histogram buckets
        for sample in REQUEST_DURATION.collect():
            for metric in sample.samples:
                if metric.name.endswith("_sum"):
                    duration_sum = metric.value
                elif metric.name.endswith("_count"):
                    count = metric.value
            return duration_sum / count if count > 0 else None
    except (
        Exception
    ):  # FIX: Ruff E722 lint - use explicit exception to avoid masking SystemExit/KeyboardInterrupt.
        return None


# Additional telemetry classes for MVP


class TelemetryCollector:
    """Collects telemetry data for geocontext operations."""

    def __init__(self):
        self.enabled = True  # Enable telemetry by default for MVP

    @asynccontextmanager
    async def track_request(self, method: str, context_hash: str):
        """Track overall request metrics."""
        if not self.enabled:
            yield {}
            return

        start_time = time.time()
        REQUEST_COUNT.labels(endpoint=method, status="started").inc()
        ACTIVE_REQUESTS.inc()

        metrics = {
            "context_hash": context_hash,
            "start_time": start_time,
            "method": method,
        }

        try:
            yield metrics
            # Success
            REQUEST_COUNT.labels(endpoint=method, status="success").inc()
            metrics["status"] = "success"

        except Exception as e:
            # Error
            REQUEST_COUNT.labels(endpoint=method, status="error").inc()
            metrics["status"] = "error"
            metrics["error"] = str(e)
            raise

        finally:
            end_time = time.time()
            duration = end_time - start_time

            REQUEST_DURATION.labels(endpoint=method).observe(duration)
            ACTIVE_REQUESTS.dec()

            metrics.update(
                {
                    "end_time": end_time,
                    "duration_seconds": duration,
                    "duration_ms": int(duration * 1000),
                }
            )

    def track_cache_miss(self, context_hash: str):
        """Track cache miss event."""
        if self.enabled:
            CACHE_OPERATIONS.labels(operation="get", result="miss").inc()

    def track_cache_hit(self, context_hash: str):
        """Track cache hit event."""
        if self.enabled:
            CACHE_OPERATIONS.labels(operation="get", result="hit").inc()

    def track_cache_set(self, context_hash: str):
        """Track cache set event."""
        if self.enabled:
            CACHE_OPERATIONS.labels(operation="set", result="success").inc()


class StructuredLogger:
    """Structured logging for geocontext operations."""

    def __init__(self):
        self.enabled = True  # Enable structured logging by default for MVP

    def log_request_start(self, context_hash: str, request_data: Dict):
        """Log request start."""
        if self.enabled:
            print(
                f"[GEOCONTEXT] REQUEST_START context_hash={context_hash} "
                f"crops={request_data.get('crops', [])} "
                f"date={request_data.get('date', 'unknown')}"
            )

    def log_request_end(self, context_hash: str, metrics: Dict):
        """Log request completion."""
        if self.enabled:
            status = metrics.get("status", "unknown")
            duration_ms = metrics.get("duration_ms", 0)
            cache_hit = metrics.get("cache_hit", False)

            print(
                f"[GEOCONTEXT] REQUEST_END context_hash={context_hash} "
                f"status={status} duration_ms={duration_ms} "
                f"cache_hit={cache_hit}"
            )

    def log_cache_operation(self, operation: str, context_hash: str, result: str):
        """Log cache operation."""
        if self.enabled:
            print(
                f"[GEOCONTEXT] CACHE operation={operation} "
                f"context_hash={context_hash} result={result}"
            )

    def log_error(self, context_hash: str, error_type: str, error_message: str):
        """Log error with context."""
        if self.enabled:
            print(
                f"[GEOCONTEXT] ERROR context_hash={context_hash} "
                f"error_type={error_type} message={error_message}"
            )


# Global instances for easy access
telemetry = TelemetryCollector()
structured_logger = StructuredLogger()
