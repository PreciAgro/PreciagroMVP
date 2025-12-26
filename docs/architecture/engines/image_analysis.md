# Image Analysis Engine – Operations Guide

## Overview

FastAPI microservice that ingests crop photos (direct upload or signed URL), runs
quality gating → classifier → CLIP fallback → optional segmentation/counting →
aggregation, and exposes a standard JSON response used by Crop Intelligence,
Temporal Logic, GeoContext, and Data Integration.

Key packages:

| Area              | Path                                                        |
|-------------------|-------------------------------------------------------------|
| API / routing     | `preciagro/packages/engines/image_analysis/app/api`         |
| Services          | `.../app/services` (analyzer, scoring, adapters)            |
| Models / schemas  | `.../app/models/schemas.py`                                 |
| Config registry   | `.../app/core/registry.py` + `config/models.yaml`           |
| Inference modules | `.../app/inference`, `.../app/segmentation`, `.../app/counting` |
| Telemetry         | `.../app/telemetry/metrics.py`                              |
| Security helpers  | `.../app/security/validators.py`                            |

## Local Runbook

```bash
pip install -r preciagro/packages/engines/image_analysis/requirements.txt
uvicorn preciagro.packages.engines.image_analysis.app.main:app --reload --port 8084
```

Environment variables (see `app/core/config.py`):

| Variable                                | Purpose                                      |
|-----------------------------------------|----------------------------------------------|
| `IMAGE_ANALYSIS_EXPLAINABILITY_ENABLED` | Enable Grad-CAM generation                   |
| `IMAGE_ANALYSIS_ALLOWED_IMAGE_HOSTS`    | Comma-separated host allowlist for signed URLs |
| `IMAGE_ANALYSIS_MAX_BASE64_BYTES`       | Max upload size for `image_base64`           |
| `IMAGE_ANALYSIS_MAX_BATCH_ITEMS`        | Batch endpoint limit                         |
| `IMAGE_ANALYSIS_MIN_CONFIDENCE_HEALTHY` | Uncertainty threshold                        |
| `ARTIFACT_STORAGE_DIR` / `ARTIFACT_BASE_URL` | Where to store Grad-CAM / mask artifacts |

JWT validation: all routes depend on `get_tenant_context` (`JWT_PUBKEY` env var).

## API Surface

| Endpoint                               | Description                                                   |
|----------------------------------------|---------------------------------------------------------------|
| `POST /api/image-analysis/analyze-image` | Analyze a single payload                                      |
| `POST /api/image-analysis/batch`         | Analyze up to `IMAGE_ANALYSIS_MAX_BATCH_ITEMS` requests       |
| `GET /api/image-analysis/health`         | Readiness probe                                               |
| `GET /`                                  | Simple landing page                                           |
| `/metrics`                               | Prometheus endpoint (enable via `ENABLE_PROMETHEUS=true`)     |

## Security + Compliance Checklist

- JWT required (FastAPI `Depends(get_tenant_context)`).
- Signed URL ingestion: host allowlist + required query token + size/time limits (`app/security/validators.py`).
- Base64 payload capped and validated on the server.
- Grad-CAM & mask artifacts written to a configurable directory; binary masks available for analytics but never shipped inline.
- Logs redact large payloads; telemetry captures latencies and counts.

## Evaluation & Release

Use the evaluation script to verify macro metrics before promotion:

```bash
python -m preciagro.packages.engines.image_analysis.eval.evaluate \
  --dataset preciagro/packages/engines/image_analysis/eval/datasets/sample_maize.yaml \
  --metrics-out reports/image_analysis/eval/sample_maize.json
```

CI (`.github/workflows/ci.yml`) runs lint/type/test for every engine, installs torch/timm/open_clip/ultralytics, and prefetches checkpoints so unit tests (which mock heavy deps) still execute deterministically.

Release checklist (T16 hardening):

1. `make -C preciagro/packages/engines/image_analysis test`
2. `make -C ... lint` and `make -C ... type`
3. `python -m ...eval.evaluate --dataset <slice>` for macro F1 ≥ 0.80 & stage accuracy ≥ 0.80
4. Upload Grad-CAM / mask artifacts to the configured bucket and verify signed URLs
5. Update downstream adapters (`app/integrations/adapters.py`) if the schema changes
