# Dependency Audit (2025-11-03)

`pip-audit` run from the repo virtual environment reports the following:

| Package | Version | Advisory | Status |
| --- | --- | --- | --- |
| starlette | 0.49.1 | GHSA-7f5h-v6xp-fcq8 | Fixed by pinning to 0.49.1 (requires FastAPI 0.121.0) |
| pip | 25.3 | GHSA-4xh5-x5gv-qwph | Fixed by upgrading the toolchain inside `.venv` |
| ecdsa | 0.19.1 | GHSA-wj6h-64fc-37mp | **Open** – latest release still flagged. Dependency of `python-jose`; monitor for a patched release or consider swapping JWT backend. |

Additional notes:
- FastAPI upgraded to 0.121.0 to remain compatible with Starlette 0.49.1.
- `requirements.txt` now pins FastAPI and Starlette to prevent regression.
- Re-run `pip-audit` after dependency bumps to confirm the `ecdsa` advisory resolves upstream.
