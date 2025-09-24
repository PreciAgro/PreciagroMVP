"""Telemetry and metrics collection for temporal logic engine."""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
from collections import defaultdict, Counter
from ..config import config

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates metrics for the temporal logic engine."""
    
    def __init__(self):
        self.enabled = config.enable_metrics
        self.metrics: Dict[str, Any] = defaultdict(int)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.gauges: Dict[str, float] = {}
        self.labels: Dict[str, Dict[str, str]] = {}
        self.start_time = datetime.utcnow()
    
    def increment(self, metric_name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        if not self.enabled:
            return
        
        key = self._build_metric_key(metric_name, labels)
        self.metrics[key] += value
        
        if labels:
            self.labels[key] = labels
    
    def record_histogram(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a value in a histogram metric."""
        if not self.enabled:
            return
        
        key = self._build_metric_key(metric_name, labels)
        self.histograms[key].append(value)
        
        # Keep only recent values (last 1000)
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
        
        if labels:
            self.labels[key] = labels
    
    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        if not self.enabled:
            return
        
        key = self._build_metric_key(metric_name, labels)
        self.gauges[key] = value
        
        if labels:
            self.labels[key] = labels
    
    def timing(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        return TimingContext(self, metric_name, labels)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        summary = {
            "counters": dict(self.metrics),
            "gauges": dict(self.gauges),
            "histograms": {},
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
        }
        
        # Calculate histogram statistics
        for key, values in self.histograms.items():
            if values:
                summary["histograms"][key] = {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p50": self._percentile(values, 50),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99)
                }
        
        return summary
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self.metrics.clear()
        self.histograms.clear()
        self.gauges.clear()
        self.labels.clear()
        self.start_time = datetime.utcnow()
    
    def _build_metric_key(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Build metric key including labels."""
        if not labels:
            return metric_name
        
        label_parts = [f"{k}={v}" for k, v in sorted(labels.items())]
        return f"{metric_name}{{{','.join(label_parts)}}}"
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, collector: MetricsCollector, metric_name: str, labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.collector.record_histogram(self.metric_name, duration, self.labels)


class TemporalEngineMetrics:
    """Specific metrics for temporal logic engine components."""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
    
    # Event metrics
    def event_received(self, event_type: str, source: str):
        """Record an event being received."""
        self.collector.increment("events_received_total", labels={
            "event_type": event_type,
            "source": source
        })
    
    def event_processed(self, event_type: str, processing_time: float, success: bool):
        """Record an event being processed."""
        self.collector.increment("events_processed_total", labels={
            "event_type": event_type,
            "status": "success" if success else "error"
        })
        self.collector.record_histogram("event_processing_duration_seconds", processing_time, labels={
            "event_type": event_type
        })
    
    # Rule metrics
    def rule_evaluated(self, rule_name: str, matches: bool, confidence: float, evaluation_time: float):
        """Record a rule evaluation."""
        self.collector.increment("rules_evaluated_total", labels={
            "rule_name": rule_name,
            "matches": str(matches).lower()
        })
        self.collector.record_histogram("rule_evaluation_duration_seconds", evaluation_time, labels={
            "rule_name": rule_name
        })
        self.collector.record_histogram("rule_confidence_score", confidence, labels={
            "rule_name": rule_name
        })
    
    def rule_triggered(self, rule_name: str, actions_count: int):
        """Record a rule being triggered."""
        self.collector.increment("rules_triggered_total", labels={
            "rule_name": rule_name
        })
        self.collector.increment("actions_scheduled_total", actions_count, labels={
            "rule_name": rule_name
        })
    
    # Task metrics
    def task_scheduled(self, task_type: str, channel: str, delay_seconds: int):
        """Record a task being scheduled."""
        self.collector.increment("tasks_scheduled_total", labels={
            "task_type": task_type,
            "channel": channel
        })
        if delay_seconds > 0:
            self.collector.record_histogram("task_delay_seconds", delay_seconds, labels={
                "task_type": task_type
            })
    
    def task_executed(self, task_type: str, channel: str, success: bool, execution_time: float, attempts: int):
        """Record a task execution."""
        self.collector.increment("tasks_executed_total", labels={
            "task_type": task_type,
            "channel": channel,
            "status": "success" if success else "error"
        })
        self.collector.record_histogram("task_execution_duration_seconds", execution_time, labels={
            "task_type": task_type,
            "channel": channel
        })
        if attempts > 1:
            self.collector.increment("task_retries_total", attempts - 1, labels={
                "task_type": task_type,
                "channel": channel
            })
    
    # Channel metrics
    def message_sent(self, channel: str, success: bool, response_time: float):
        """Record a message being sent."""
        self.collector.increment("messages_sent_total", labels={
            "channel": channel,
            "status": "success" if success else "error"
        })
        self.collector.record_histogram("message_send_duration_seconds", response_time, labels={
            "channel": channel
        })
    
    def message_delivery_status(self, channel: str, status: str):
        """Record message delivery status."""
        self.collector.increment("message_delivery_status_total", labels={
            "channel": channel,
            "status": status
        })
    
    # Rate limiting metrics
    def rate_limit_applied(self, limit_type: str, user_id: str, delay_seconds: int):
        """Record rate limiting being applied."""
        self.collector.increment("rate_limits_applied_total", labels={
            "limit_type": limit_type
        })
        self.collector.record_histogram("rate_limit_delay_seconds", delay_seconds, labels={
            "limit_type": limit_type
        })
    
    def quiet_hours_applied(self, channel: str, delay_seconds: int):
        """Record quiet hours policy being applied."""
        self.collector.increment("quiet_hours_applied_total", labels={
            "channel": channel
        })
        self.collector.record_histogram("quiet_hours_delay_seconds", delay_seconds, labels={
            "channel": channel
        })
    
    # System metrics
    def set_active_rules_count(self, count: int):
        """Set the count of active rules."""
        self.collector.set_gauge("active_rules_count", count)
    
    def set_pending_tasks_count(self, count: int):
        """Set the count of pending tasks."""
        self.collector.set_gauge("pending_tasks_count", count)
    
    def set_queue_depth(self, queue_name: str, depth: int):
        """Set queue depth."""
        self.collector.set_gauge("queue_depth", depth, labels={
            "queue": queue_name
        })


class HealthChecker:
    """Health checking for temporal logic engine components."""
    
    def __init__(self):
        self.checks: Dict[str, Dict[str, Any]] = {}
        self.last_check_time: Optional[datetime] = None
    
    def register_check(self, name: str, check_func, timeout: int = 10):
        """Register a health check."""
        self.checks[name] = {
            "func": check_func,
            "timeout": timeout,
            "last_status": "unknown",
            "last_check": None,
            "last_error": None
        }
    
    def run_all_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all registered health checks."""
        results = {}
        overall_healthy = True
        
        for name, check_config in self.checks.items():
            try:
                start_time = time.time()
                status = check_config["func"]()
                duration = time.time() - start_time
                
                results[name] = {
                    "status": "healthy" if status else "unhealthy",
                    "duration_seconds": duration,
                    "last_check": datetime.utcnow().isoformat(),
                    "error": None
                }
                
                self.checks[name].update({
                    "last_status": "healthy" if status else "unhealthy",
                    "last_check": datetime.utcnow(),
                    "last_error": None
                })
                
                if not status:
                    overall_healthy = False
            
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "duration_seconds": 0,
                    "last_check": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
                
                self.checks[name].update({
                    "last_status": "error",
                    "last_check": datetime.utcnow(),
                    "last_error": str(e)
                })
                
                overall_healthy = False
        
        self.last_check_time = datetime.utcnow()
        
        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "checks": results,
            "check_time": self.last_check_time.isoformat()
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary without running checks."""
        if not self.last_check_time:
            return {"status": "unknown", "message": "No health checks run yet"}
        
        healthy_checks = sum(1 for check in self.checks.values() if check["last_status"] == "healthy")
        total_checks = len(self.checks)
        
        if healthy_checks == total_checks:
            status = "healthy"
        elif healthy_checks > 0:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "healthy_checks": healthy_checks,
            "total_checks": total_checks,
            "last_check": self.last_check_time.isoformat()
        }


# Global instances
metrics_collector = MetricsCollector()
engine_metrics = TemporalEngineMetrics(metrics_collector)
health_checker = HealthChecker()


# Register default health checks
def check_database_connection():
    """Default database health check."""
    # In real implementation, test database connection
    return True

def check_redis_connection():
    """Default Redis health check."""
    # In real implementation, test Redis connection
    return True

def check_memory_usage():
    """Check memory usage."""
    import psutil
    memory_percent = psutil.virtual_memory().percent
    return memory_percent < 90  # Unhealthy if over 90% memory usage

# Register checks
health_checker.register_check("database", check_database_connection)
health_checker.register_check("redis", check_redis_connection)

try:
    import psutil
    health_checker.register_check("memory", check_memory_usage)
except ImportError:
    logger.info("psutil not available, skipping memory health check")
