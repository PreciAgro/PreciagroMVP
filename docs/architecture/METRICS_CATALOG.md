# Metrics Catalog

Comprehensive catalog of all Prometheus metrics used in PreciagroMVP.

## Application Metrics

### HTTP Requests

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | service, endpoint, method, status | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | service, endpoint, method | Request latency (p50, p95, p99) |
| `http_errors_total` | Counter | service, status_code, error_type | HTTP errors (4xx, 5xx) |

### Sessions

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sessions_created_total` | Counter | service, tenant | Sessions created |
| `sessions_active` | Gauge | service, tenant | Currently active sessions |
| `sessions_terminated_total` | Counter | service, tenant, reason | Sessions terminated |

### Intent Classification

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `intent_classifications_total` | Counter | service, intent, confidence_level | Total classifications |
| `intent_classification_accuracy` | Gauge | service, time_window | Classification accuracy (0-1) |

---

## Infrastructure Metrics

### System Resources

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `service_cpu_percent` | Gauge | service | CPU usage % |
| `service_memory_bytes` | Gauge | service | Memory usage in bytes |
| `service_memory_percent` | Gauge | service | Memory usage % |

### Database

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `db_connections_active` | Gauge | service, pool_name | Active connections |
| `db_connections_idle` | Gauge | service, pool_name | Idle connections |
| `db_connections_total` | Gauge | service, pool_name | Total connections |
| `db_connection_errors_total` | Counter | service, error_type | Connection errors |

### Redis

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `redis_operations_total` | Counter | service, operation, status | Total operations |
| `redis_operation_duration_seconds` | Histogram | service, operation | Operation latency |

### Disk I/O

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `disk_read_bytes_total` | Counter | service | Bytes read |
| `disk_write_bytes_total` | Counter | service | Bytes written |

### Network I/O

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `network_tx_bytes_total` | Counter | service | Bytes transmitted |
| `network_rx_bytes_total` | Counter | service | Bytes received |

---

## Business Metrics

### Users

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `active_users_total` | Gauge | tenant, time_window | Active users |
| `user_queries_total` | Counter | tenant, user_id | Total queries |
| `queries_per_user` | Histogram | tenant | Queries per user distribution |

### Tool Usage

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `tool_calls_total` | Counter | tool_name, success | Total tool calls |
| `tool_call_duration_seconds` | Histogram | tool_name | Tool call latency |
| `tool_call_success_rate` | Gauge | tool_name | Success rate (0-1) |

### RAG

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rag_retrievals_total` | Counter | success, num_results | Total retrievals |
| `rag_retrieval_duration_seconds` | Histogram | - | Retrieval latency |
| `rag_relevance_score` | Histogram | - | Relevance scores (0-1) |

### User Satisfaction

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `user_satisfaction_score` | Histogram | tenant | Satisfaction scores (1-5) |
| `user_feedback_total` | Counter | tenant, rating, feedback_type | Feedback events |

---

## Usage Examples

### Application Metrics

```python
from preciagro.packages.shared.metrics_middleware import add_metrics_middleware
from preciagro.packages.shared.system_monitor import start_system_monitoring

app = FastAPI()

# Automatic HTTP metrics
add_metrics_middleware(app, "my-service")

# System resource monitoring
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_system_monitoring("my-service")
    yield
    stop_system_monitoring()
```

### Business Metrics

```python
from preciagro.packages.shared import metrics

# Track tool calls
with metrics.tool_call_duration_seconds.labels(tool_name="search").time():
    result = await search_tool(query)
    metrics.tool_calls_total.labels(
        tool_name="search",
        success=str(result.success)
    ).inc()

# Track RAG relevance
metrics.rag_relevance_score.observe(relevance_score)
```

---

## Querying Metrics

### Prometheus Queries

**Request Rate (req/s)**:
```promql
rate(http_requests_total[5m])
```

**Error Rate**:
```promql
rate(http_errors_total{error_type="5xx"}[5m])
```

**Latency p95**:
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Active Users**:
```promql
active_users_total{time_window="1h"}
```

**Tool Success Rate**:
```promql
rate(tool_calls_total{success="true"}[5m])
/
rate(tool_calls_total[5m])
```

---

## Grafana Dashboards

- **Application Metrics**: Request rate, latency, errors
- **Infrastructure**: CPU, memory, DB connections
- **Business KPIs**: Users, queries, satisfaction
