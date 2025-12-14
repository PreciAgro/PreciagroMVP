# GeoContext Engine Run Guide

This guide covers dependency setup, running the GeoContext FastAPI service, and executing the automated checks.

## 1. Prerequisites
- Python 3.11
- pip
- Optional services: PostgreSQL + PostGIS, Redis
- GDAL/PROJ runtime when working with real spatial data (see troubleshooting)
- Make (optional)

## 2. Install Dependencies
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```
If you jump between engines, expose the repo root:
```
$env:PYTHONPATH = "$PWD"
```

## 3. Environment Variables
Use `.env.example` as a template or export manually:
```
$env:DEV_MODE = "true"
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/geo"
$env:ENABLE_POSTGIS = "false"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:ALLOWED_HOSTS = "localhost,127.0.0.1,testserver"
$env:JWT_PUBKEY = ""         # optional in dev mode
```
With `DEV_MODE=true` the test suite accepts a stub JWT and falls back to seeded datasets when PostGIS or Redis are unavailable.

## 4. Run the Service
```
make -C preciagro/packages/engines/geo_context run
```
Manual command:
```
uvicorn preciagro.packages.engines.geo_context.api.main:app --host 0.0.0.0 --port 8102 --reload
```
Endpoints:
- `GET /` – service metadata
- `GET /health` – health probe
- `POST /v1/resolve` – resolve a field context
- `GET /metrics` – Prometheus metrics (requires auth header when auth is enabled)

## 5. Tests and Tooling
```
pytest preciagro/packages/engines/geo_context/tests -q
make -C preciagro/packages/engines/geo_context lint
make -C preciagro/packages/engines/geo_context type   # baseline emits legacy issues
make -C preciagro/packages/engines/geo_context audit
```

## 6. Smoke Test
Use the dev token from the tests while `DEV_MODE=true`:
```
$token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlciIsInRlbmFudF9pZCI6ImRldi10ZW5hbnQiLCJzY29wZXMiOlsiKiJdfQ.ZGV2LXNpZ25hdHVyZQ"

curl -X POST http://localhost:8102/v1/resolve `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d @preciagro/packages/engines/geo_context/tests/fixtures/polygons/pl_warsaw.geojson
```

## 7. Troubleshooting
| Symptom | Cause | Fix |
| --- | --- | --- |
| 401 responses | Missing auth header | Use the dev token (DEV_MODE) or configure `JWT_PUBKEY` |
| Invalid host error | Host not in `ALLOWED_HOSTS` | Append host to the comma separated list |
| Spatial lookups fail | PostGIS disabled | Set `ENABLE_POSTGIS=false` for fallback data or provision PostGIS |
| GDAL/PROJ errors | Native libs missing | Install GDAL 3.x and PROJ 9.x, set `GDAL_DATA` and `PROJ_LIB` |

## 8. Next Steps
- Enable PostGIS and Redis in development to validate live resolvers.
- Document additional rules in `rules/*.yaml` and extend the rules engine accordingly.
- Promote the API smoke tests into CI once auth and infrastructure dependencies are stable.
