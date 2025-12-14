# PreciagroMVP Observability Stack

This directory contains the observability infrastructure for monitoring, tracing, and error tracking.

## Components

### Prometheus
- **Port**: 9090
- **Purpose**: Metrics collection and alerting
- **Scrapes**: All engine `/prometheus` or `/metrics` endpoints
- **Config**: `prometheus/prometheus.yml`
- **Alerts**: `prometheus/alerts.yml`

### Grafana
- **Port**: 3000
- **Default credentials**: admin/admin
- **Purpose**: Visualization and dashboards
- **Dashboards**:
  - System Overview
  - Database Metrics
  - Redis Metrics

### Jaeger
- **UI Port**: 16686
- **OTLP Port**: 4318
- **Purpose**: Distributed tracing
- **Protocol**: OTLP over HTTP

### Alertmanager
- **Port**: 9093
- **Purpose**: Alert routing and notifications
- **Config**: `prometheus/alertmanager.yml`

### Exporters
- **Redis Exporter**: Port 9121
- **PostgreSQL Exporter**: Port 9187

## Quick Start

### Start the observability stack:
```bash
docker-compose -f docker-compose.observability.yml up -d
```

### Access UIs:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Alertmanager: http://localhost:9093

### Stop the stack:
```bash
docker-compose -f docker-compose.observability.yml down
```

## Configuration

### Sentry (Optional)
Add to your `.env` file:
```env
SENTRY_DSN=your-sentry-dsn-here
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

### OpenTelemetry
Configured via environment variables:
```env
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=your-service-name
```

## Alert Rules

Located in `prometheus/alerts.yml`:
- Service downtime
- High error rates (>5%)
- High latency (p95 > 1s)
- Database connection issues
- Redis memory usage
- Notification failures

## Customization

### Adding New Scrape Targets
Edit `prometheus/prometheus.yml`:
```yaml
- job_name: 'new-service'
  static_configs:
    - targets: ['host.docker.internal:PORT']
  metrics_path: '/metrics'
```

### Adding Dashboards
Place JSON files in `grafana/dashboards/` - they will be auto-loaded.

### Configuring Alert Receivers
Edit `prometheus/alertmanager.yml` to add Slack, email, or webhook integrations.
