# Data Integration Engine Run Guide

This run book explains how to bootstrap the Data Integration engine, run the shared API gateway, and execute the automated checks. All commands are Windows PowerShell friendly; adjust paths if you prefer bash.

## 1. Prerequisites
- Python 3.11 (repo tested with 3.11)
- pip
- Optional services: PostgreSQL, Redis, OpenWeather API key
- Make (optional but recommended for the per-engine Makefile targets)

## 2. Install Dependencies
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```
If you switch between engines in the same shell, expose the repo root:
```
$env:PYTHONPATH = "$PWD"
```

## 3. Environment Variables
Copy `.env.example` in this directory to `.env` or export the variables manually:
```
$env:DEV = "1"                             # load .env automatically
$env:OPENWEATHER_API_KEY = ""               # optional live connector key
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/preciagro"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:INGEST_RATE_LIMIT_QPS = "5"
```
Leave `OPENWEATHER_API_KEY` empty to rely on stubbed responses. Integration tests skip automatically when `DATABASE_URL` or `REDIS_URL` are missing.

## 4. Run the Service
The engine is mounted on the shared API gateway. Use the dedicated make target or run uvicorn directly.
```
make -C preciagro/packages/engines/data_integration run
```
Manual command:
```
uvicorn preciagro.apps.api_gateway.main:app --host 0.0.0.0 --port 8101 --reload
```
Key endpoints:
- Health: `GET http://localhost:8101/healthz`
- Metrics: `GET http://localhost:8101/metrics`
- Trigger ingest: `POST http://localhost:8101/ingest/run/openweather?lat=-33.45&lon=-70.66&scope=hourly`

## 5. Tests and Tooling
```
.venv\Scripts\Activate.ps1
pytest preciagro/packages/engines/data_integration/tests -q
make -C preciagro/packages/engines/data_integration lint
make -C preciagro/packages/engines/data_integration type   # mypy (baseline still noisy)
make -C preciagro/packages/engines/data_integration audit  # pip-audit wrapper
```
Integration tests that touch Redis/PostgreSQL skip when the services are unavailable.

## 6. Smoke Testing
```
$body = '{"lat": -33.45, "lon": -70.66, "scope": "hourly"}'
curl -X POST http://localhost:8101/ingest/run/openweather `
  -H "Content-Type: application/json" `
  -d $body
```
Query recent normalized items (requires PostgreSQL):
```
curl "http://localhost:8101/ingest/items?kind=weather.forecast&limit=10"
```

## 7. Troubleshooting
| Symptom | Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError` for `preciagro.*` | `PYTHONPATH` not set | Activate the virtualenv and export `$env:PYTHONPATH = "$PWD"` |
| `asyncpg` import error | Dependencies not installed | Re-run `pip install -r requirements.txt` |
| `503 OpenWeather API key not configured` | Missing key | Provide `OPENWEATHER_API_KEY` or accept stubbed responses |
| DB/Redis connection errors | Services offline | Start local containers or update the URLs |

## 8. Next Steps
- Wire the event bus (`bus/consumer.py`) into your messaging stack once you replace the stub consumer.
- Add additional connectors by registering them in `pipeline/orchestrator.py` and exposing `POST /ingest/run/{source}` handlers.
- Promote the integration tests that hit PostgreSQL/Redis into CI once those services are available in the test environment.
