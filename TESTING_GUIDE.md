# PreciAgro MVP - Testing & Development Guide

## Table of Contents
- [Quick Start](#quick-start)
- [Environment Setup](#environment-setup)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Database Management](#database-management)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites
- Python 3.9+
- Docker Desktop (for database services)
- PowerShell (Windows)

### 1. Setup Environment
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Services
```powershell
# Start database services
docker-compose up -d postgres redis

# Apply database migrations
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"
alembic upgrade head
```

### 3. Run Application
```powershell
# Start the API server
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"
uvicorn preciagro.apps.api_gateway.main:app --host 127.0.0.1 --port 8000 --reload
```

## Environment Setup

### Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Command Prompt)
.venv\Scripts\activate.bat

# Deactivate
deactivate
```

### Dependencies
```powershell
# Install all requirements
pip install -r requirements.txt

# Install additional packages for development
pip install pytest pytest-asyncio httpx
```

## Running the Application

### Local Development (In-Memory Database)
```powershell
# Quick start with SQLite in-memory
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"
uvicorn preciagro.apps.api_gateway.main:app --host 127.0.0.1 --port 8000 --reload
```

### With PostgreSQL Database
```powershell
# Start PostgreSQL service
docker-compose up -d postgres

# Set database URL
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"

# Apply migrations
alembic upgrade head

# Start application
uvicorn preciagro.apps.api_gateway.main:app --host 127.0.0.1 --port 8000 --reload
```

### With Full Services (PostgreSQL + Redis)
```powershell
# Start all services
docker-compose up -d

# Set database URL
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"

# Apply migrations
alembic upgrade head

# Start application
uvicorn preciagro.apps.api_gateway.main:app --host 127.0.0.1 --port 8000 --reload
```

## Testing

### Unit Tests with Pytest

#### Run All Tests
```powershell
# Run all unit tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=preciagro

# Run specific test file
pytest preciagro/packages/engines/temporal_logic/tests/test_temporal.py
```

#### Run Specific Tests
```powershell
# Run specific test class
pytest preciagro/packages/engines/temporal_logic/tests/test_temporal.py::TestModels

# Run specific test method
pytest preciagro/packages/engines/temporal_logic/tests/test_temporal.py::TestModels::test_temporal_event_creation

# Run tests matching pattern
pytest -k "test_temporal"
```

#### Integration Tests
```powershell
# Run integration tests (requires PostgreSQL and Redis)
docker-compose up -d
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"
alembic upgrade head
pytest preciagro/packages/engines/data_integration/tests/test_integration_db_redis.py
```

### Endpoint Tests with PowerShell Scripts

#### Quick API Tests
```powershell
# Test basic endpoints (requires running server)
.\test_quick.ps1

# Test all temporal endpoints  
.\test_all_endpoints.ps1

# Test with clean setup
.\test_temporal_endpoints_clean.ps1

# Final comprehensive test
.\test_final.ps1
```

#### Manual API Testing
```powershell
# Test main diagnose endpoint
$body = @{
    image_base64 = "BASE64_STRING_HERE"
    crop_hint = "tomato"
    location = @{
        lat = 52.23
        lng = 21.01
    }
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/v1/diagnose-and-plan" -Method POST -Body $body -ContentType "application/json"

# Test health endpoint
Invoke-WebRequest -Uri "http://localhost:8000/temporal/health" -Method GET
```

### Automated Testing Script
```powershell
# Use the integration script
.\scripts\run_integration.ps1
```

## Database Management

### Alembic Migrations
```powershell
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade migrations
alembic downgrade -1

# Check migration status
alembic current
alembic history
```

### Database Setup
```powershell
# Start PostgreSQL
docker-compose up -d postgres

# Initialize database with migrations
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"
alembic upgrade head

# Reset database (development only!)
docker-compose down postgres
docker-compose up -d postgres
Start-Sleep -Seconds 5
alembic upgrade head
```

## Development Workflow

### Daily Development
1. **Activate Environment**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Start Services** (if needed)
   ```powershell
   docker-compose up -d postgres redis
   ```

3. **Run Application**
   ```powershell
   $env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"
   uvicorn preciagro.apps.api_gateway.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Test Changes**
   ```powershell
   # Run unit tests
   pytest

   # Test endpoints
   .\test_quick.ps1
   ```

### Code Quality
```powershell
# Format code (if black is installed)
pip install black
black preciagro/

# Lint code (if flake8 is installed)
pip install flake8
flake8 preciagro/

# Type checking (if mypy is installed)
pip install mypy
mypy preciagro/
```

## Testing Strategy

### Test Types

#### 1. Unit Tests (pytest)
- **Location**: preciagro/packages/engines/*/tests/
- **Purpose**: Test individual components in isolation
- **Run**: pytest

#### 2. Integration Tests (pytest)
- **Location**: preciagro/packages/engines/data_integration/tests/test_integration_db_redis.py
- **Purpose**: Test components working together with real services
- **Requirements**: PostgreSQL + Redis
- **Run**: .\scripts\run_integration.ps1

#### 3. API Endpoint Tests (PowerShell)
- **Location**: 	est_*.ps1 files
- **Purpose**: End-to-end testing of HTTP endpoints
- **Requirements**: Running server
- **Run**: .\test_all_endpoints.ps1

### Test Execution Order
1. **Unit Tests First**: pytest
2. **Integration Tests**: .\scripts\run_integration.ps1
3. **API Tests**: .\test_all_endpoints.ps1

## Available Test Scripts

### PowerShell Test Scripts
- 	est_quick.ps1 - Basic health and intents endpoints
- 	est_all_endpoints.ps1 - Complete endpoint test suite
- 	est_temporal_endpoints.ps1 - Temporal logic specific tests
- 	est_temporal_endpoints_clean.ps1 - Clean temporal endpoint tests
- 	est_final.ps1 - Final comprehensive test suite
- 	est_simple.ps1 - Simple endpoint validation

### Python Test Scripts
- 	est_temporal_endpoints.py - Python-based endpoint tests
- 	est_dispatcher.py - Dispatcher component tests

## Environment Variables

### Database Configuration
```powershell
# SQLite (Development)
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# PostgreSQL (Production-like)
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"
```

### Redis Configuration
```powershell
$env:REDIS_URL = "redis://localhost:6379"
```

## API Endpoints

### Main Application
- **POST** /v1/diagnose-and-plan - Main diagnosis and planning endpoint
- **GET** /docs - API documentation (Swagger UI)

### Temporal Logic Engine
- **GET** /temporal/health - Health check
- **GET** /temporal/intents - Get available intents
- **GET** /temporal/schedule/{user_id} - Get user schedule
- **POST** /temporal/events - Ingest events
- **POST** /temporal/outcomes - Record outcomes

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```powershell
# Ensure PostgreSQL is running
docker-compose ps postgres

# Check if port is available
netstat -an | findstr :5432

# Restart PostgreSQL
docker-compose restart postgres
```

#### 2. Virtual Environment Issues
```powershell
# Recreate virtual environment
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### 3. Port Already in Use
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID [PID] /F
```

#### 4. Migration Issues
```powershell
# Reset migrations (development only!)
docker-compose down
docker volume prune -f
docker-compose up -d postgres
Start-Sleep -Seconds 5
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"
alembic upgrade head
```

### Test Failures

#### API Test Failures
- Ensure the server is running: uvicorn preciagro.apps.api_gateway.main:app --host 127.0.0.1 --port 8000
- Check if the correct DATABASE_URL is set
- Verify all services are running: docker-compose ps

#### Unit Test Failures
- Check Python environment: python --version
- Ensure all dependencies are installed: pip install -r requirements.txt
- Run tests in isolation: pytest path/to/specific/test.py -v

## Project Structure

```
PreciagroMVP/
 preciagro/                    # Main package
    apps/
       api_gateway/          # FastAPI application
    packages/
        engines/
            temporal_logic/   # Temporal logic engine
            data_integration/ # Data integration
            crop_intel/       # Crop intelligence
            geo_context/      # Geographic context
            image_analysis/   # Image analysis
            inventory/        # Inventory management
 alembic/                      # Database migrations
 scripts/                      # Utility scripts
 test_*.ps1                    # PowerShell test scripts
 test_*.py                     # Python test scripts
 docker-compose.yml            # Service orchestration
 requirements.txt              # Python dependencies
 pytest.ini                   # Test configuration
```

## Contributing

### Before Committing
1. Run all tests: pytest
2. Test endpoints: .\test_all_endpoints.ps1
3. Check code formatting
4. Update documentation if needed

### Making Changes
1. Create feature branch
2. Make changes
3. Add/update tests
4. Run test suite
5. Create pull request

---

For more detailed information about specific components, refer to the README.md files in individual engine packages.
