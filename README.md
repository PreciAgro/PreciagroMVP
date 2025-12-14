# PreciAgro Monorepo

PreciAgro bundles multiple engines (data integration, temporal logic, geo context) plus several skeleton engines used for future work. This README summarises prerequisites, bootstrap flows, and the current engine lineup.

## Prerequisites
- Python 3.11
- pip
- Optional: PostgreSQL, PostGIS, Redis, Docker (for services)
- Make (for convenience targets)

## Quick Start
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```
Run all active test suites:
```
pytest preciagro/packages/engines/data_integration/tests -q
pytest preciagro/packages/engines/temporal_logic/tests -q
pytest preciagro/packages/engines/geo_context/tests -q
```
Each engine exposes a Makefile; for example:
```
make -C preciagro/packages/engines/data_integration lint
```

## Engine Matrix
| Engine | Status | Language | Run Command | Test Command |
| --- | --- | --- | --- | --- |
| data-integration | ACTIVE | Python | `uvicorn preciagro.apps.api_gateway.main:app --host 0.0.0.0 --port 8101 --reload` | `pytest preciagro/packages/engines/data_integration/tests -q` |
| temporal-logic | ACTIVE | Python | `uvicorn preciagro.packages.engines.temporal_logic.app:app --host 0.0.0.0 --port 8100 --reload` | `pytest preciagro/packages/engines/temporal_logic/tests -q` |
| geo-context | ACTIVE | Python | `uvicorn preciagro.packages.engines.geo_context.api.main:app --host 0.0.0.0 --port 8102 --reload` | `pytest preciagro/packages/engines/geo_context/tests -q` |
| conversational-nlp | EXPERIMENTAL | Python | `uvicorn preciagro.packages.engines.conversational_nlp.app:app --host 0.0.0.0 --port 8103 --reload` | `pytest preciagro/packages/engines/conversational_nlp/tests -q` |
| crop-intelligence | SKELETON | Python | - | - |
| image-analysis | SKELETON | Python | - | - |
| inventory | SKELETON | Python | - | - |

Detailed run books live under each engine: `preciagro/packages/engines/<engine>/docs/` (see `RUN.md` and, when applicable, `API.md`).

## Tooling Configuration
- `.editorconfig` and `pyproject.toml` define formatting, linting, and type-check settings shared across engines.
- `mypy.ini` enables gradual typing with strict rules opt-in per module.
- `.github/workflows/ci.yml` executes install → lint → type → test across active engines.

## Secrets Management
The project uses `python-dotenv` and `pydantic-settings` for configuration and secret management.
1.  Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
2.  Update `.env` with your local secrets (API keys, DB credentials).
3.  **Never commit `.env` to version control.** It is already in `.gitignore`.
4.  For production (e.g., GitHub Actions, Docker), set these values as environment variables or secrets.

## Security and Auditing
Run `make audit` in each engine directory (wrapper around `pip-audit`). Current known vulnerability: `ecdsa` 0.19.1 (transitive dependency of `python-jose`) — upstream fix pending.

## References
- `reports/engine_matrix.json` mirrors the table above in machine-readable form.
- `reports/dependency_audit.md` lists dependency findings and mitigation notes.
- `reports/integrations_checklist.md` tracks external systems required by each engine.
