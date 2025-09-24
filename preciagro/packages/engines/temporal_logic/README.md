# Temporal Logic Engine

The Temporal Logic Engine is a core component of the PreciagroMVP platform that processes farming events and schedules automated tasks based on configurable business rules.

## Overview

This engine listens for events from other systems (weather forecasts, soil sensors, disease diagnostics) and automatically schedules farming tasks when predefined conditions are met. It supports complex temporal logic with time windows, deduplication, and farmer timezone handling.

## Quick Start

### Running the Engine

```bash
# Start the FastAPI server
uvicorn preciagro.packages.engines.temporal_logic.app:app --host 127.0.0.1 --port 8000

# With environment variables
DATABASE_URL="sqlite+aiosqlite:///:memory:" uvicorn preciagro.packages.engines.temporal_logic.app:app --reload
```

### Basic Usage

```python
from preciagro.packages.engines.temporal_logic.dispatcher_minimal import TemporalLogicEngine
from preciagro.packages.engines.temporal_logic.contracts import EngineEvent

# Create engine instance
engine = TemporalLogicEngine()

# Process an event
event = EngineEvent(
    topic="weather.forecast",
    id="weather_001",
    ts_utc=datetime.now(timezone.utc),
    farm_id="farm_123",
    farmer_tz="UTC",
    payload={"temperature": 35, "humidity": 45}
)

# Process event and get scheduled tasks
await engine.process_event(event, session)
```

## Architecture

```
temporal_logic/
 API Layer
    app.py                 # FastAPI application
    api/                   # HTTP endpoints
        routes/
           events.py      # POST /temporal/events
           schedules.py   # GET /temporal/schedule  
           outcomes.py    # GET /temporal/outcomes
           intents.py     # GET /temporal/intents
        middleware/

 Core Engine
    dispatcher_minimal.py # Main engine logic
    contracts.py          # Pydantic models
    models.py             # SQLAlchemy ORM models
    evaluator.py          # Rule evaluation engine
    compiler.py           # Task compilation

 Rule System
    dsl/                  # Domain Specific Language
       loader.py         # Rule loading
       parser.py         # Rule parsing
    rules/                # Business rule definitions
    policies/             # Rate limiting & scheduling

 Data & Storage
    storage/
       db.py            # Database connections
    migrations/          # Alembic migrations
    telemetry/           # Metrics & monitoring

 Testing
     tests/               # Unit & integration tests
     scripts/             # Test utilities
```

## Core Components

### 1. Event Dispatcher (dispatcher_minimal.py)
The heart of the engine that processes incoming events:

- **Event Processing**: Matches events against business rules
- **Rule Evaluation**: Evaluates conditional logic (temperature, humidity, etc.)
- **Task Scheduling**: Creates scheduled tasks with proper timing
- **Database Integration**: Persists tasks using SQLAlchemy async sessions

```python
class TemporalLogicEngine:
    async def process_event(self, event: EngineEvent, session) -> List[str]
    def find_matching_rules(self, event: EngineEvent) -> List[Rule]
    async def create_tasks_for_rule(self, rule: Rule, event: EngineEvent, session) -> str
```

### 2. Contract Models (contracts.py)
Pydantic models defining the data structures:

- **EngineEvent**: Incoming events from other systems
- **Rule**: Business rule definitions with triggers and actions
- **Trigger**: Event matching criteria (topic, conditions)
- **Clause**: Individual conditions (temperature > 30, humidity < 60)
- **Message**: Task definitions with scheduling information

### 3. Database Models (models.py)
SQLAlchemy ORM models for persistence:

- **ScheduleItem**: Scheduled farming tasks
- **TaskOutcome**: Task execution results
- **Database Sessions**: Async session management

### 4. FastAPI Application (app.py)
HTTP API server with endpoints:

- **Health**: /temporal/health - System status
- **Events**: /temporal/events - Event ingestion  
- **Schedule**: /temporal/schedule - View scheduled tasks
- **Outcomes**: /temporal/outcomes - Task results
- **Intents**: /temporal/intents - Rule definitions

## Business Rules

The engine includes 3 production farming automation rules:

### 1. Weather Spraying Rule
**Trigger**: weather.forecast
**Conditions**: 
- Temperature > 30C
- Humidity < 60%
**Action**: Schedule spraying task in 60 minutes
**Purpose**: Optimal conditions for pesticide/herbicide application

### 2. Soil Irrigation Rule  
**Trigger**: soil.moisture_update
**Conditions**:
- Moisture level < 30%
**Action**: Schedule irrigation in 30 minutes
**Purpose**: Prevent crop stress from drought

### 3. Disease Prevention Rule
**Trigger**: diagnosis.outcome 
**Conditions**:
- Risk level in ['high', 'critical']  
- Disease type in ['blight', 'fungal', 'bacterial']
**Action**: Schedule treatment in 4 hours
**Purpose**: Rapid response to disease outbreaks

## Testing

The engine includes comprehensive test coverage:

### Run All Tests
```bash
# From project root
.\run-tests.ps1 -TestType all

# Python tests only  
.\run-tests.ps1 -TestType python

# Quick validation
.\run-tests.ps1 -TestType quick
```

### Individual Tests
```bash
# Set environment
$env:PYTHONPATH = $PWD.Path
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test all business rules
python tests\test_all_rules.py

# Test simple engine functionality
python tests\test_simple_engine.py

# Test API endpoints
tests\test_quick.ps1
```

### Test Coverage
- All 3 business rules (weather, soil, disease)
- Event processing and rule matching
- Task creation and database persistence
- HTTP API endpoints (5/5)
- Error handling and edge cases
- Timezone handling and scheduling
- Database migrations and models

## API Endpoints

### POST /temporal/events
Process a new farming event:

```bash
curl -X POST "http://localhost:8000/temporal/events" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "weather.forecast",
    "id": "weather_001", 
    "ts_utc": "2025-01-09T10:00:00Z",
    "farm_id": "farm_123",
    "farmer_tz": "UTC",
    "payload": {
      "temperature": 35,
      "humidity": 45
    }
  }'
```

**Response**: 
```json
{
  "tasks_created": 1,
  "task_ids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

### GET /temporal/schedule
Retrieve scheduled tasks:

```bash
curl "http://localhost:8000/temporal/schedule?farm_id=farm_123"
```

**Response**:
```json
{
  "count": 2,
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_type": "spray_reminder",
      "scheduled_utc": "2025-01-09T12:00:00Z",
      "priority": "high",
      "farm_id": "farm_123"
    }
  ]
}
```

### Other Endpoints
- GET /temporal/outcomes - View task execution results
- GET /temporal/intents - View active business rules
- GET /temporal/health - System health check

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/preciagro"
DATABASE_URL="sqlite+aiosqlite:///:memory:"  # For testing

# API Settings  
HOST="127.0.0.1"
PORT=8000
RELOAD=true

# Logging
LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

## Development

### Setup Development Environment
```bash
# Clone repository
git clone https://github.com/PreciAgro/PreciagroMVP.git
cd PreciagroMVP

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn preciagro.packages.engines.temporal_logic.app:app --reload
```

### Adding New Rules
1. Define rule in dispatcher_minimal.py _load_default_rules() method
2. Add test cases in tests/test_all_rules.py
3. Update API documentation  
4. Run test suite to verify functionality

---

**Version**: 1.0  
**Last Updated**: January 2025  
**Status**: Production Ready  
**Test Coverage**: 35/35 Requirements Met
