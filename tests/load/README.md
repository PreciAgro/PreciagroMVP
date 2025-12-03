# Load Testing with Locust

This directory contains load testing scenarios for PreciagroMVP using Locust.

## Quick Start

### Install Dependencies
```bash
pip install locust
```

### Run Load Tests

#### Test API Gateway
```bash
locust -f locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2
```

#### Test Specific Service
```bash
# Conversational NLP
locust -f locustfile.py --host=http://localhost:8101 ConversationalUser --users 5 --spawn-rate 1

# Temporal Logic
locust -f locustfile.py --host=http://localhost:8100 TemporalLogicUser --users 10 --spawn-rate 2
```

### Web UI
Open http://localhost:8089 to access the Locust web interface where you can:
- Start/stop load tests
- Adjust user count and spawn rate
- View real-time statistics
- Download reports

## Test Scenarios

### APIGatewayUser
- **Target**: API Gateway (port 8000)
- **Tasks**:
  - Health check (75% of requests)
  - Metrics endpoint (25% of requests)
- **Wait time**: 1-3 seconds

### ConversationalUser
- **Target**: Conversational NLP (port 8101)
- **Tasks**:
  - Send chat messages
- **Wait time**: 2-5 seconds

### TemporalLogicUser
- **Target**: Temporal Logic Engine (port 8100)
- **Tasks**:
  - Create events (33% of requests)
  - Health check (67% of requests)
- **Wait time**: 3-7 seconds

## Performance Baselines

Record baseline performance metrics:

### API Gateway
- **RPS**: Target >1000 req/s
- **P95 Latency**: <100ms
- **Error Rate**: <1%

### Conversational NLP
- **RPS**: Target >100 req/s
- **P95 Latency**: <500ms (AI processing)
- **Error Rate**: <2%

### Temporal Logic
- **RPS**: Target >500 req/s
- **P95 Latency**: <200ms
- **Error Rate**: <1%

## Running Load Tests

### CLI Mode (Headless)
```bash
locust -f locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m --html report.html
```

### Distributed Mode
```bash
# Master
locust -f locustfile.py --master

# Workers (on same or different machines)
locust -f locustfile.py --worker --master-host=localhost
```

## Tips

1. **Start Small**: Begin with 10-20 users, increase gradually
2. **Monitor Resources**: Watch CPU, memory, database connections
3. **Use Realistic Data**: Vary test data to avoid caching effects
4. **Test Incrementally**: Test one service at a time before full stack
5. **Record Results**: Save reports for comparison over time

## Troubleshooting

- **Connection Errors**: Ensure services are running
- **High Error Rates**: May indicate capacity limits or bugs
- **Slow Ramping**: Increase spawn-rate
- **Resource Exhaustion**: Reduce user count or use distributed mode
