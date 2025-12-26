# Fix Report (Data Integration, Temporal Logic, GeoContext)

## Highlights
- Normalised documentation across active engines (`docs/RUN.md`, `docs/API.md`) with ASCII-only content, consistent troubleshooting notes, and explicit commands per engine.
- Upgraded FastAPI to 0.121.0 and pinned Starlette 0.49.1 in `requirements.txt` to remediate GHSA-7f5h-v6xp-fcq8; pip upgraded to 25.3; recorded outstanding `ecdsa` advisory.
- Added `.editorconfig`, `pyproject.toml`, `mypy.ini`, and a matrix-based GitHub Actions workflow (`.github/workflows/ci.yml`) covering install → lint → type (soft fail) → tests for all active engines.
- Refined GeoContext endpoint tests to surface payload metadata and removed emoji characters that confused lint/type tooling (# FIX comments embedded near the adjustments).
- Brought Temporal Logic compiler, quiet-hours policy, rate-limits placeholder, and tests into lint compliance (# FIX annotations inline) after running `black`, `isort`, and `ruff` across active engines.

## Tests Executed
- `pytest preciagro/packages/engines/data_integration/tests -q`
- `pytest preciagro/packages/engines/temporal_logic/tests -q`
- `pytest preciagro/packages/engines/geo_context/tests -q`
- `pip-audit` (see dependency report for results)

## Follow-ups
- Full-project `mypy` still fails because of legacy modules. New `mypy.ini` scopes strict checks to changed files; plan incremental fixes before enabling a hard failure in CI.
- `ecdsa` vulnerability remains open upstream; monitor python-jose releases for a patched dependency.
