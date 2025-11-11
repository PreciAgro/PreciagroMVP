# Crop Intelligence Engine Runbook

## 1. Service Overview
- **Service name:** Crop Intelligence Engine (CIE)
- **Entrypoint:** `preciagro.packages.engines.crop_intelligence.app.main:app`
- **Port:** 8082 (configurable via `PORT`)
- **Dependencies:** Postgres, optional Redis, GeoContext, Temporal Logic, Data Integration, Image Analysis.

## 2. Environment & Secrets
- Copy `.env.example` to `.env` or inject vars via your orchestrator.
- Required env:
  - `DATABASE_URL` – Postgres DSN (`postgresql+psycopg2://user:pass@host:port/db`)
  - `API_AUTH_TOKEN` – inbound header token (`X-PreciAgro-Token`)
  - `SERVICE_AUTH_TOKEN` – used for outbound calls to sibling services.
  - `GEOCONTEXT_BASE_URL`, `DATA_INTEGRATION_BASE_URL`, `TEMPORAL_LOGIC_BASE_URL`, `IMAGE_ANALYSIS_BASE_URL`
  - `ENABLE_PROMETHEUS` – set to `true` to expose `/metrics`

Rotate tokens via your secret manager and update the deployment. Service reload required.

## 3. Database & Migrations
1. Ensure Postgres is reachable.
2. Run `alembic upgrade head` (automatically executed in Docker entrypoint if `DATABASE_URL` is set).
3. Seeds: use the dataset exporter or custom SQL to pre-populate ontology tables.

## 4. Starting & Stopping
- **Docker:** `docker build -t cie .` then `docker run --env-file ./preciagro/packages/engines/crop_intelligence/.env.example -p 8082:8082 cie`
- **Compose:** see root `docker-compose.yml` service `cie`.
- **Local dev:** `.\\preciagro\\packages\\engines\\crop_intelligence\\run_cie.ps1` (uses uvicorn reload).
- Stop via `docker stop <container>` or Ctrl+C for local dev.

## 5. Health & Metrics
- Health: `GET /` returns `{status:"operational"}`
- Metrics: `GET /metrics` (Prometheus format) when `ENABLE_PROMETHEUS=true`.
- Logs: stdout/stderr. Use structured logging stack if available.

## 6. Operating Procedures
- **Deploy:** build container, push, update orchestrator. Ensure migrations ran.
- **Model updates:** upload new artifacts, update `config/models.json`, restart service.
- **Backfill/export:** run `python -m preciagro.packages.engines.crop_intelligence.data.export_datasets --output-dir artifacts`.
- **Incident response:** check DB connectivity, dependent services, and logs. For auth failures ensure `X-PreciAgro-Token` matches `API_AUTH_TOKEN`.

## 7. Troubleshooting Cheatsheet
| Symptom | Check |
| --- | --- |
| 401 errors | `API_AUTH_TOKEN` mismatch |
| 500 on /crop endpoints | DB schema not migrated; run `alembic upgrade head` |
| Missing soil data | GeoContext base URL / credentials |
| Metrics missing | `ENABLE_PROMETHEUS` set? `/metrics` mounted? |

Escalate unresolved incidents to the platform team with logs, recent changes, and failing endpoint details.
