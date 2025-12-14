# PreciAgro Active Engine Run & Test Guide

This playbook explains how to start every engine that currently ships in the MVP and how to run the test suites that keep them healthy. Each test entry includes what it validates so you can decide when to run it.

---

## Quick Reference

| Engine | Run Command (Dev) | Primary Test Runner |
| --- | --- | --- |
| Data Integration | `uvicorn preciagro.apps.api_gateway.main:app --reload --port 8000` | `.\scripts\run_data_tests.ps1` |
| Temporal Logic | `uvicorn preciagro.packages.engines.temporal_logic.app:app --reload --port 8001` | `.\scripts\run_temporal_tests.ps1` |
| GeoContext | `uvicorn preciagro.apps.api_gateway.main:app --reload --port 8000` (same gateway exposes `/api/v1/geocontext/*`) | `.\scripts\run_geo_tests.ps1` |
| Crop Intelligence | `uvicorn preciagro.packages.engines.crop_intelligence.app.main:app --reload --port 8082` | `.\scripts\run_crop_tests.ps1` |
| Image Analysis | `uvicorn preciagro.packages.engines.image_analysis.app.main:app --reload --port 8084` | `pytest preciagro/packages/engines/image_analysis/tests -q` |

Run commands assume you already exported the required environment variables (covered below) and activated your virtual environment.

---

## Shared Local Setup

1. **Python environment** – `python -m venv .venv && .\.venv\Scripts\Activate.ps1`, then `pip install -r requirements.txt`.
2. **Datastores** – `docker-compose up -d postgres redis` to get PostgreSQL + Redis for engines that need them. (Data Integration and Temporal Logic can also use SQLite for tests.)
3. **Migrations** – `alembic upgrade head` against whichever `DATABASE_URL` you exported.
4. **Environment variables** – Common ones:
   - `DATABASE_URL` (engine-specific; SQLite `sqlite+aiosqlite:///:memory:` works for most tests)
   - `REDIS_URL` (when Redis-backed features are exercised)
   - `DEV=1` to enable local shortcuts in the shared API gateway
   - Connector/API keys (e.g., `OPENWEATHER_API_KEY` for Data Integration, JWT keys for Image Analysis security)

---

## Data Integration Engine

### Run It
1. `docker-compose up -d postgres redis` (Postgres for storage, Redis for the event bus).
2. `setx OPENWEATHER_API_KEY "<key>"` (or export in-session) plus `DATABASE_URL`, `REDIS_URL`, `ENVIRONMENT`, `LOG_LEVEL`.
3. `uvicorn preciagro.apps.api_gateway.main:app --reload --port 8000`.
4. Hit `/healthz` and `/ingest/run/openweather` to trigger ingestion jobs as described in `preciagro/packages/engines/data_integration/README.md`.

### Test Suites & What They Cover

| Command | What it Validates | Notes |
| --- | --- | --- |
| `.\scripts\run_data_tests.ps1` | Runs every test under `preciagro/packages/engines/data_integration/tests` against an in-memory SQLite DB. Catches schema regressions, orchestrator wiring bugs, and connector contract drift without needing Docker. | Sets `PYTHONPATH` + `DATABASE_URL` automatically. |
| `pytest preciagro/packages/engines/data_integration/tests/test_smoke_orchestrator.py -q` | Uses a mock connector to drive `pipeline.orchestrator.run_job` end-to-end, asserting that normalized items are upserted and published exactly once. Great quick check after editing orchestrator or normalizers. | No external services required. |
| `pytest preciagro/packages/engines/data_integration/tests/test_inprocess_scheduler_consumer.py -q` | Boots the demo scheduler inside `preciagro.apps.api_gateway.main` and ensures it can be cancelled cleanly. Proves that async tasks start/stop without Redis/Postgres. | Helpful after touching scheduler bootstrap code. |
| `pytest preciagro/packages/engines/data_integration/tests/test_integration_db_redis.py -q` | Runs only when `DATABASE_URL` and `REDIS_URL` point to live services. Verifies that normalization produces hashes/IDs and that the Redis/DB code paths don’t raise. | Skip by default; wire up Docker services before running. |
| `.\scripts\run_integration.ps1` | Automates Docker startup, Alembic upgrade, and then executes the Redis/Postgres integration test above. | Use this when validating CI-like flows on Windows. |

**When to run what**
- After connector or normalization edits → `test_smoke_orchestrator.py`
- After scheduler/event-bus changes → `test_inprocess_scheduler_consumer.py`
- Before merging to `main` → entire suite via `run_data_tests.ps1`, then (optionally) `run_integration.ps1` if you touched I/O paths.

---

## Temporal Logic Engine

### Run It
1. Export `DATABASE_URL=sqlite+aiosqlite:///:memory:` (good for dev) or point to Postgres.
2. `uvicorn preciagro.packages.engines.temporal_logic.app:app --host 127.0.0.1 --port 8001 --reload`.
3. Use `test_temporal_endpoints.ps1` (below) or curl to hit `/temporal/health`, `/temporal/events`, `/temporal/schedule`, etc.

### Core Pytest Suite

| Command | Coverage Highlights |
| --- | --- |
| `.\scripts\run_temporal_tests.ps1` | Executes `preciagro/packages/engines/temporal_logic/tests`. `test_contracts.py` asserts Pydantic contracts (clauses, triggers, dedupe windows) stay backward compatible. `test_simple.py` exercises the DSL evaluator/compiler utilities. `test_temporal.py` spins up an async SQLite DB to validate ORM models, policies (rate limits, quiet hours), Twilio/WhatsApp channel hooks, metrics, and an end-to-end workflow from event ingestion to scheduled task creation. |

### Scenario & CLI Tests (under `/tests`)

| Command | What It Teaches You |
| --- | --- |
| `python tests/test_simple_engine.py` | Creates an in-memory DB, feeds a weather event through `TemporalLogicEngine`, and inspects the persisted schedule rows. Use it to understand rule matching and dedupe IDs. |
| `python tests/test_engine_direct.py` | Similar to the above but drives the global `dispatcher_minimal.engine` instance and inspects DB contents, helping debug rule definitions in place. |
| `python tests/test_all_rules.py` | Crafts weather, soil, and disease events to make sure all three production rules trigger and persist tasks. Great regression harness before shipping rule changes. |
| `python tests/test_dispatcher.py` | Smoke-tests imports plus instantiation of the dispatcher to ensure DSL/telemetry modules still load (useful after refactors). |
| `powershell -File tests/test_temporal_endpoints.ps1` | Hits the live HTTP API (health, intents, POST /events, GET /schedule, POST /outcomes) with representative payloads. Requires the server running on `http://127.0.0.1:8000` or adjust the script. |
| Variants (`test_temporal_endpoints_clean.ps1`, `test_quick.ps1`, `test_simple.ps1`, `test_final.ps1`, `test_real_engine.ps1`, `test_all_endpoints.ps1`) | Each script dials up/down verbosity or target environments (e.g., clean DB vs. seeded). Use them when you need repeatable demos of the HTTP experience. |

**Suggested Flow**
1. `run_temporal_tests.ps1` after every change inside `preciagro/packages/engines/temporal_logic`.
2. `python tests/test_all_rules.py` before adjusting DSL rules or dedupe scopes.
3. One of the PowerShell endpoint scripts before a demo or when validating the FastAPI routes end-to-end.

---

## GeoContext Engine

### Run It
1. Start backing services if you want real data (`docker-compose up -d postgres redis`).
2. Export `DATABASE_URL` (SQLite works for tests). For endpoint tests you also need a JWT token; set `JWT_TOKEN` or edit the script to use the dev token in `test_api_smoke.py`.
3. The GeoContext routes are already mounted inside `preciagro.apps.api_gateway.main`, so `uvicorn preciagro.apps.api_gateway.main:app --reload --port 8000` exposes `/api/v1/geocontext/*`.

### Automated Tests

| Command | What it Covers |
| --- | --- |
| `.\scripts\run_geo_tests.ps1` (or `run_geo_tests_root.ps1`) | Runs everything under `preciagro/packages/engines/geo_context/tests` with in-memory SQLite. It wires the `PYTHONPATH` for you. |
| `pytest preciagro/packages/engines/geo_context/tests/test_api_smoke.py -q` | Uses `httpx.AsyncClient` against the ASGI app to hit `/v1/resolve` for Poland and Zimbabwe polygons, verifying cache toggles, centroid math, and authorization headers. |
| `pytest preciagro/packages/engines/geo_context/tests/test_api.py -q` | Focuses on validation edge cases (bad polygons, missing crops, auth failures). Run after altering request/response models or security deps. |
| `pytest preciagro/packages/engines/geo_context/tests/test_resolver_pipeline.py -q` | Exercises `pipeline.resolver.FieldContextResolver`, ensuring spatial, soil, climate, and calendar resolvers compose correctly even with missing data. |
| `pytest preciagro/packages/engines/geo_context/tests/test_golden_snapshots.py -q` | Compares resolver output against golden JSON fixtures for Warsaw and Murewa polygons. Perfect for spotting regressions after changing rules or climate math. |
| `python preciagro/packages/engines/geo_context/tests/run_tests.py` | CLI harness that can generate fixture outputs and optionally rebaseline golden files. Useful when adding new regions. |
| `python preciagro/packages/engines/geo_context/test_endpoints.py` or `.\preciagro\packages\engines\geo_context\test_endpoints.ps1` | Asynchronous HTTP probes that hit the running gateway, optionally saving JSON outputs for later analysis. Great smoke test before handing off to QA. |

**Tip:** After editing YAML rules (e.g., `rules/*.yaml`), run both `test_resolver_pipeline.py` and `test_golden_snapshots.py` to ensure human-readable calendars stay stable.

---

## Crop Intelligence Engine (CIE)

### Run It
1. `uvicorn preciagro.packages.engines.crop_intelligence.app.main:app --reload --port 8082`.
2. Set `API_AUTH_TOKEN` if you want auth enabled; otherwise leave blank for local dev.
3. Use `demo_workflow.py` or the PowerShell script below to simulate field onboarding.

### Tests & Scripts

| Command | Purpose |
| --- | --- |
| `.\scripts\run_crop_tests.ps1` | Runs all FastAPI + physics tests under `preciagro/packages/engines/crop_intelligence/tests`. The suite stands up a TestClient, so no external services needed. |
| `pytest preciagro/packages/engines/crop_intelligence/tests/test_smoke.py -q` | Full API smoke: register field → push telemetry → read `/cie/field/state`, `/cie/status`, `/cie/field/actions`, `/cie/feedback`, `/cie/recommend-actions`, `/cie/predict-yield`, `/cie/schedule`, `/crop/*` mirrors. Ensures round-trip recommendations and crop APIs continue to work. |
| `pytest preciagro/packages/engines/crop_intelligence/tests/test_quick_qa.py -q` | Heavy unit coverage for water physics, disease physics, and confidence math. Useful when tweaking agronomic heuristics or sensor ingest logic. |
| `pytest preciagro/packages/engines/crop_intelligence/tests/test_export_datasets.py -q` | Verifies `data.export_datasets` writes CSVs with the expected columns, ensuring the learning hooks keep producing clean training sets. |
| `powershell -File preciagro/packages/engines/crop_intelligence/test_cie.ps1` | Hits the live service on port 8082, checking health, field registration, telemetry ingest, recommendations, and feedback loops. Ideal as a pre-demo checklist. |
| `powershell -File preciagro/packages/engines/crop_intelligence/test_cie_pilot_uat.ps1` | Extended version with pilot-ready payloads; run when you need to simulate production-like traffic. |

**Flow Suggestion**
- Edit FastAPI routes? → run `test_smoke.py`.
- Change physics modules? → run `test_quick_qa.py`.
- Touch dataset export or feedback handling? → run `test_export_datasets.py` plus the PowerShell smoke script.

---

## Image Analysis Engine

### Run It
1. Install extra requirements: `pip install -r preciagro/packages/engines/image_analysis/requirements.txt`.
2. Optional: install CUDA-enabled torch if you have a GPU.
3. `uvicorn preciagro.packages.engines.image_analysis.app.main:app --reload --port 8084`.
4. Export `IMAGE_ANALYSIS_API_PREFIX`, `IMAGE_ANALYSIS_ALLOWED_IMAGE_HOSTS`, and `JWT_PUBKEY` (or `DEV_MODE=true`) as needed.

### Tests & Coverage

| Command | What Gets Verified |
| --- | --- |
| `pytest preciagro/packages/engines/image_analysis/tests -q` | Runs the full suite described below. All tests mock heavy ML dependencies so they finish quickly even without torch/timm. |
| `pytest .../test_classifier_head.py -q` | Ensures classifier heads reuse cached timm models, gracefully fall back to the heuristic stub when torch/timm is missing, and emit consistent label scores. |
| `pytest .../test_segmentation.py -q` | Validates that SAM/segmentation toggles respect config flags and that lesion masks are generated or skipped appropriately. |
| `pytest .../test_counting.py -q` | Confirms object-counting heads gate correctly on request flags and produce deterministic counts. |
| `pytest .../test_scoring.py -q` | Asserts health score aggregation logic (quality gate + classifier + lesion coverage) stays stable. |
| `pytest .../test_security.py -q` | Exercises JWT enforcement and allowed-host validation so untrusted image URLs or unsigned requests get rejected. |
| `pytest .../test_integrations.py -q` | Checks the adapters that reshape `ImageAnalysisResponse` for other engines, ensuring schema drift doesn’t break downstream consumers. |
| `pytest .../test_batch_gateway_integration.py -q` | Spins up the FastAPI app with `TestClient` to hit `/api/image-analysis/batch`, verifying batching, error reporting, and artifact URL plumbing. |

**When to Run**
- Any change under `app/inference` or `app/services` → rerun classifier/segmentation/counting/scoring tests.
- Any API contract or security change → rerun `test_batch_gateway_integration.py` + `test_security.py`.
- Before tagging a release → run the entire suite and spot-check Grad-CAM artifacts under `reports/image_analysis/artifacts`.

---

## After Running Tests

1. **Review outputs** – fix failures, re-run the impacted suite.
2. **Pre-commit checklist** – `pytest` (repo root), `ruff`, and `mypy` if your workflow includes them.
3. **Document** – When you create new tests or scripts, add them here so future teammates know what they cover.

Happy testing! If something feels missing, append a new section with the same structure so this guide stays the single source of truth.
