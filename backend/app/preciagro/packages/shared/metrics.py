"""Shared metrics module for comprehensive application, infrastructure, and business metrics."""

from __future__ import annotations

import logging
from prometheus_client import Counter, Gauge, Histogram, Info

logger = logging.getLogger(__name__)

# ============================================================================
# APPLICATION METRICS
# ============================================================================

# Request/Response metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['service', 'endpoint', 'method', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['service', 'endpoint', 'method'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_errors_total = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['service', 'status_code', 'error_type']
)

# Session metrics
sessions_created_total = Counter(
    'sessions_created_total',
    'Total sessions created',
    ['service', 'tenant']
)

sessions_active = Gauge(
    'sessions_active',
    'Currently active sessions',
    ['service', 'tenant']
)

sessions_terminated_total = Counter(
    'sessions_terminated_total',
    'Total sessions terminated',
    ['service', 'tenant', 'reason']
)

# Intent classification metrics
intent_classifications_total = Counter(
    'intent_classifications_total',
    'Total intent classifications',
    ['service', 'intent', 'confidence_level']
)

intent_classification_accuracy = Gauge(
    'intent_classification_accuracy',
    'Intent classification accuracy (0-1)',
    ['service', 'time_window']
)

# ============================================================================
# INFRASTRUCTURE METRICS
# ============================================================================

# System resources
service_cpu_percent = Gauge(
    'service_cpu_percent',
    'CPU usage percentage',
    ['service']
)

service_memory_bytes = Gauge(
    'service_memory_bytes',
    'Memory usage in bytes',
    ['service']
)

service_memory_percent = Gauge(
    'service_memory_percent',
    'Memory usage percentage',
    ['service']
)

# Database connection pool
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections',
    ['service', 'pool_name']
)

db_connections_idle = Gauge(
    'db_connections_idle',
    'Idle database connections',
    ['service', 'pool_name']
)

db_connections_total = Gauge(
    'db_connections_total',
    'Total database connections',
    ['service', 'pool_name']
)

db_connection_errors_total = Counter(
    'db_connection_errors_total',
    'Database connection errors',
    ['service', 'error_type']
)

# Redis metrics (in addition to redis_exporter)
redis_operations_total = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['service', 'operation', 'status']
)

redis_operation_duration_seconds = Histogram(
    'redis_operation_duration_seconds',
    'Redis operation latency',
    ['service', 'operation']
)

# Disk I/O
disk_read_bytes_total = Counter(
    'disk_read_bytes_total',
    'Total bytes read from disk',
    ['service']
)

disk_write_bytes_total = Counter(
    'disk_write_bytes_total',
    'Total bytes written to disk',
    ['service']
)

# Network I/O
network_tx_bytes_total = Counter(
    'network_tx_bytes_total',
    'Total bytes transmitted',
    ['service']
)

network_rx_bytes_total = Counter(
    'network_rx_bytes_total',
    'Total bytes received',
    ['service']
)

# ============================================================================
# BUSINESS METRICS
# ============================================================================

# User metrics
active_users_total = Gauge(
    'active_users_total',
    'Total active users',
    ['tenant', 'time_window']
)

user_queries_total = Counter(
    'user_queries_total',
    'Total user queries',
    ['tenant', 'user_id']
)

queries_per_user = Histogram(
    'queries_per_user',
    'Distribution of queries per user',
    ['tenant'],
    buckets=(1, 5, 10, 25, 50, 100, 250, 500)
)

# Tool usage metrics
tool_calls_total = Counter(
    'tool_calls_total',
    'Total tool calls',
    ['tool_name', 'success']
)

tool_call_duration_seconds = Histogram(
    'tool_call_duration_seconds',
    'Tool call duration',
    ['tool_name'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

tool_call_success_rate = Gauge(
    'tool_call_success_rate',
    'Tool call success rate (0-1)',
    ['tool_name']
)

# RAG metrics
rag_retrievals_total = Counter(
    'rag_retrievals_total',
    'Total RAG retrievals',
    ['success', 'num_results']
)

rag_retrieval_duration_seconds = Histogram(
    'rag_retrieval_duration_seconds',
    'RAG retrieval latency'
)

rag_relevance_score = Histogram(
    'rag_relevance_score',
    'RAG retrieval relevance scores',
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

# User satisfaction
user_satisfaction_score = Histogram(
    'user_satisfaction_score',
    'User satisfaction scores',
    ['tenant'],
    buckets=(1, 2, 3, 4, 5)
)

user_feedback_total = Counter(
    'user_feedback_total',
    'Total user feedback events',
    ['tenant', 'rating', 'feedback_type']
)

# Service info
service_info = Info(
    'service_info',
    'Service information',
    ['service', 'version', 'environment']
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def record_http_request(service: str, endpoint: str, method: str, status: int, duration: float) -> None:
    """Record HTTP request metrics.
    
    Args:
        service: Service name
        endpoint: API endpoint
        method: HTTP method
        status: HTTP status code
        duration: Request duration in seconds
    """
    http_requests_total.labels(service=service, endpoint=endpoint, method=method, status=status).inc()
    http_request_duration_seconds.labels(service=service, endpoint=endpoint, method=method).observe(duration)
    
    # Track errors separately
    if status >= 400:
        error_type = '4xx' if 400 <= status < 500 else '5xx'
        http_errors_total.labels(service=service, status_code=status, error_type=error_type).inc()


def record_session_event(service: str, tenant: str, event_type: str, reason: str = None) -> None:
    """Record session lifecycle events.
    
    Args:
        service: Service name
        tenant: Tenant ID
        event_type: 'created', 'active', or 'terminated'
        reason: Termination reason (if terminated)
    """
    if event_type == 'created':
        sessions_created_total.labels(service=service, tenant=tenant).inc()
    elif event_type == 'terminated':
        sessions_terminated_total.labels(service=service, tenant=tenant, reason=reason or 'normal').inc()


def update_system_metrics(service: str, cpu_percent: float, memory_bytes: int, memory_percent: float) -> None:
    """Update system resource metrics.
    
    Args:
        service: Service name
        cpu_percent: CPU usage percentage
        memory_bytes: Memory usage in bytes
        memory_percent: Memory usage percentage
    """
    service_cpu_percent.labels(service=service).set(cpu_percent)
    service_memory_bytes.labels(service=service).set(memory_bytes)
    service_memory_percent.labels(service=service).set(memory_percent)
