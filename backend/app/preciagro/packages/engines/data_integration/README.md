# Data Integration Engine

The Data Integration Engine is responsible for ingesting, normalizing, and storing external data sources (like weather data) into the PreciAgro system. It provides a pluggable architecture for adding new data connectors and normalizers.

## Features

- **Pluggable Connectors**: Support for multiple data sources (OpenWeather, etc.)
- **Data Normalization**: Transforms raw data into standardized formats
- **Rate Limiting**: Built-in QPS controls for API calls
- **Event-Driven**: Publishes events via Redis for downstream processing  
- **Monitoring**: Prometheus metrics integration
- **Background Processing**: Automated data ingestion scheduler

## Architecture

```
        
   Connectors     ->    Normalizers    ->     Storage      
 (OpenWeather)          (Pipeline)         (PostgreSQL)    
        
                                                      
        
                                
                        
                           Event Bus     
                            (Redis)      
                        
```

## Prerequisites

1. **Python 3.11+**
2. **PostgreSQL** (for data storage)
3. **Redis** (for event bus and caching)
4. **OpenWeather API Key** (for weather data)

## Quick Start

### 1. Start Dependencies

The easiest way to start PostgreSQL and Redis is using Docker Compose from the project root:

```powershell
# From project root directory
docker-compose up -d postgres redis
```

Wait for the services to be ready (about 10-15 seconds), then verify they're running:

```powershell
# Check if PostgreSQL is ready
docker-compose ps postgres

# Check if Redis is ready  
docker-compose ps redis
```

### 2. Set Environment Variables

Create a .env file in the project root or set environment variables:

```powershell
# Required environment variables
$env:DEV = "1"
$env:OPENWEATHER_API_KEY = "your_api_key_here"
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:ENVIRONMENT = "development"
$env:LOG_LEVEL = "INFO"
```

**Get an OpenWeather API Key:**
1. Register at [OpenWeatherMap](https://openweathermap.org/api)
2. Get your free API key from the dashboard
3. Replace your_api_key_here with your actual key

### 3. Install Dependencies

```powershell
# Install Python packages
pip install -r requirements.txt
```

### 4. Run Database Migrations

```powershell
# Apply database schema migrations
alembic upgrade head
```

### 5. Start the API Gateway

```powershell
# Start the FastAPI server with the data integration engine
uvicorn preciagro.apps.api_gateway.main:app --reload --port 8000
```

The server will start on http://localhost:8000

### 6. Test the Engine

Check if the service is running:

```powershell
curl http://localhost:8000/healthz
```

Test weather data ingestion:

```powershell
# Ingest current weather for London
Invoke-WebRequest -Uri "http://localhost:8000/ingest/run/openweather?lat=51.5074&lon=-0.1278&scope=current" -Method POST

# Ingest hourly forecast for Santiago, Chile
Invoke-WebRequest -Uri "http://localhost:8000/ingest/run/openweather?lat=-33.45&lon=-70.6667&scope=hourly" -Method POST

# Ingest daily forecast for São Paulo, Brazil  
Invoke-WebRequest -Uri "http://localhost:8000/ingest/run/openweather?lat=-23.55&lon=-46.6333&scope=daily" -Method POST
```

Check ingested data:

```powershell
curl http://localhost:8000/ingest/items
```

## API Endpoints

### Health Check
- **GET** /healthz - Service health status

### Data Ingestion  
- **POST** /ingest/run/openweather - Trigger OpenWeather data ingestion
  - Query Parameters:
    - lat (float): Latitude coordinate
    - lon (float): Longitude coordinate  
    - scope (string): Data scope - "current", "hourly", or "daily"

### Data Retrieval
- **GET** /ingest/items - List all normalized data items

### Monitoring
- **GET** /metrics - Prometheus metrics endpoint

## Configuration

Configuration is handled via environment variables using Pydantic Settings:

| Variable | Default | Description |
|----------|---------|-------------|
| OPENWEATHER_API_KEY | None | OpenWeather API key (required) |
| DATABASE_URL | postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro | PostgreSQL connection string |
| REDIS_URL | 
edis://localhost:6379/0 | Redis connection string |
| INGEST_RATE_LIMIT_QPS | 5 | Rate limit for API calls (queries per second) |
| DEV | None | Set to "1" to load .env file in development |

## Development

### Running Tests

```powershell
# Run all tests
pytest

# Run only data integration tests
pytest preciagro/packages/engines/data_integration/tests/

# Run integration tests (requires running DB + Redis)
pytest preciagro/packages/engines/data_integration/tests/test_integration_db_redis.py

# Run smoke tests
pytest preciagro/packages/engines/data_integration/tests/test_smoke_orchestrator.py -v
```

### Using the Integration Script

There's a convenient PowerShell script that starts dependencies and runs integration tests:

```powershell
# From project root
.\scripts\run_integration.ps1
```

This script will:
1. Start PostgreSQL and Redis via Docker Compose
2. Wait for services to be ready
3. Apply database migrations
4. Run integration tests

### Project Structure

```
preciagro/packages/engines/data_integration/
 README.md                 # This file
 config.py                # Configuration settings
 bus/                     # Event bus (Redis pub/sub)
    consumer.py         # Event consumer
    publisher.py        # Event publisher
 connectors/             # External data source connectors
    base.py            # Base connector interface
    openweather.py     # OpenWeather API connector
    http_json.py       # Generic HTTP JSON connector
    mock_connector.py  # Mock connector for testing
 contracts/             # Data contracts and schemas
    v1/
        normalized_item.py  # Normalized data schema
 pipeline/              # Data processing pipeline
    orchestrator.py    # Main orchestration logic
    normalize_weather.py   # Generic weather normalizer
    normalize_openweather.py  # OpenWeather-specific normalizer
 routers/              # FastAPI route handlers
    ingest.py         # Ingestion endpoints
 storage/              # Data persistence
    db.py            # Database operations
 tests/                # Test suite
     conftest.py       # Test configuration
     test_integration_db_redis.py  # Integration tests
     test_smoke_orchestrator.py   # Smoke tests
     test_inprocess_scheduler_consumer.py  # Scheduler tests
```

## Adding New Data Sources

To add a new data connector:

1. **Create Connector**: Implement BaseConnector in connectors/
2. **Create Normalizer**: Add normalization logic in pipeline/
3. **Register**: Add to the orchestrator's source registry
4. **Add Routes**: Create API endpoints in 
outers/
5. **Test**: Add tests in 	ests/

Example connector structure:

```python
from .base import BaseConnector

class MyDataConnector(BaseConnector):
    async def fetch(self, **kwargs):
        # Fetch data from external source
        pass
        
    async def normalize(self, raw_data, **kwargs):  
        # Transform to NormalizedItem format
        pass
```

## Monitoring & Observability

The engine includes built-in monitoring:

- **Prometheus Metrics**: Available at /metrics
- **Health Checks**: Available at /healthz  
- **Logging**: Structured logging with configurable levels
- **Rate Limiting**: Built-in QPS controls

Key metrics:
- preciagro_ingest_jobs_total - Total ingestion jobs by source and scope

## Troubleshooting

### Common Issues

1. **"OpenWeather API key not configured"**
   - Ensure OPENWEATHER_API_KEY environment variable is set
   - Verify the API key is valid at [OpenWeatherMap](https://openweathermap.org)

2. **Database connection errors**
   - Check if PostgreSQL is running: docker-compose ps postgres
   - Verify DATABASE_URL environment variable
   - Run migrations: lembic upgrade head

3. **Redis connection errors**  
   - Check if Redis is running: docker-compose ps redis
   - Verify REDIS_URL environment variable

4. **Rate limiting errors**
   - Adjust INGEST_RATE_LIMIT_QPS environment variable
   - Check your API provider's rate limits

### Debugging

Enable debug logging:

```powershell
$env:LOG_LEVEL = "DEBUG"
```

Check service logs:

```powershell
# View PostgreSQL logs
docker-compose logs postgres

# View Redis logs  
docker-compose logs redis
```

## Production Considerations

- Use proper secrets management for API keys
- Configure appropriate rate limits for your API quotas
- Set up monitoring and alerting for failed ingestion jobs
- Consider using connection pooling for high-throughput scenarios
- Implement data retention policies for normalized items
- Use Redis persistence for critical event data

## License

This is part of the PreciAgro MVP project.