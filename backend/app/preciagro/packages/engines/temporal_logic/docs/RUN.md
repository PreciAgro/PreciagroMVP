# Temporal Logic Engine Run Guide

Covers local setup for the Temporal Logic engine, including dependencies, run commands, and testing workflow.

## 1. Prerequisites
- Python 3.11
- pip
- PostgreSQL (asyncpg) and Redis for realistic runs
- Optional channel credentials: Twilio SMS, WhatsApp Business
- Make (optional)

## 2. Install Dependencies
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```
Expose the repo when calling modules directly:
```
$env:PYTHONPATH = "$PWD"
```

## 3. Environment Variables
Copy `.env.example` or export manually:
```
$env:DEV = "1"
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/temporal"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:ENABLE_WORKER = "false"
$env:LOG_LEVEL = "INFO"
$env:MAX_NOTIFS_PER_DAY = "5"
$env:DIGEST_HOUR_LOCAL = "19"
$env:SERVICE_JWT_PUBLIC_KEY = ""  # optional during development
$env:TWILIO_ACCOUNT_SID = ""
$env:TWILIO_AUTH_TOKEN = ""
$env:TWILIO_FROM = ""
$env:WHATSAPP_TOKEN = ""
$env:WHATSAPP_PHONE_ID = ""
```
Set `ENABLE_WORKER=true` only when Redis and PostgreSQL are available.

## 4. Run the Service
```
make -C preciagro/packages/engines/temporal_logic run
```
Manual command:
```
uvicorn preciagro.packages.engines.temporal_logic.app:app --host 0.0.0.0 --port 8100 --reload
```
Endpoints:
- `GET /` – service metadata
- `GET /temporal/health`
- `POST /temporal/events`
- `POST /temporal/outcomes`
- `GET /temporal/schedule/{user_id}`
- `GET /metrics`

## 5. Tests and Tooling
```
pytest preciagro/packages/engines/temporal_logic/tests -q
make -C preciagro/packages/engines/temporal_logic lint
make -C preciagro/packages/engines/temporal_logic type   # baseline emits legacy issues
make -C preciagro/packages/engines/temporal_logic audit
```

## 6. Smoke Tests
Create an example event:
```
curl -X POST http://localhost:8100/temporal/events `
  -H "Content-Type: application/json" `
  -d '{"topic":"weather.forecast","id":"wx-001","ts_utc":"2025-11-02T12:00:00Z","farm_id":"farm-123","farmer_tz":"Africa/Johannesburg","payload":{"temperature":35,"humidity":45}}'
```
List scheduled tasks:
```
curl "http://localhost:8100/temporal/schedule/farmer-123?days_ahead=7"
```

## 7. Troubleshooting
| Symptom | Cause | Fix |
| --- | --- | --- |
| Redis connection errors | `REDIS_URL` wrong or Redis not running | Start Redis locally or update the URL |
| `asyncpg.errors.InvalidCatalogName` | Database missing | Create the database referenced in `DATABASE_URL` |
| Worker crashes on exit | Background worker still running | Set `ENABLE_WORKER=false` while testing |
| `401 Unauthorized` (future) | JWT public key configured without token | Provide a valid token or clear `SERVICE_JWT_PUBLIC_KEY` during dev |

## 8. Next Steps
- Wire the worker pool into the production scheduler once Redis is stable.
- Replace the legacy Pydantic v1 validators in `contracts_old.py` with v2 `field_validator` to silence warnings.
- Add integration tests that cover signed JWT verification once the shared security client is fully enabled.
