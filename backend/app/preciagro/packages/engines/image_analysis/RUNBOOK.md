# Image Analysis Engine – On-Call Runbook

## 1. Basic Facts

- **Service**: `preciagro.packages.engines.image_analysis`
- **Port**: 8084 (FastAPI + Prometheus on `/metrics`)
- **Dependencies**: Postgres (metadata via downstream), Blob storage (artifact uploads), JWT gateway, Torch/timm/open-clip/ultralytics checkpoints.
- **Config entry point**: `app/core/config.py`

## 2. Common Alerts & Fixes

| Alert / Symptom | Likely Cause | Mitigation |
|-----------------|-------------|------------|
| High latency / timeout | Cold starts or missing checkpoints | Ensure checkpoint cache volume is mounted; confirm `python -m ...prefetch_checkpoints` runs on deploy |
| Quality gate failures spike | Blurry uploads from field app | Check `quality_notes` in logs; coordinate with client to improve capture instructions |
| Unauthenticated requests rejected | Missing JWT or clock skew | Verify API Gateway attaches `Authorization: Bearer`; ensure deployment has `JWT_PUBKEY` |
| Grad-CAM / mask URLs 404 | Artifact storage misconfigured | Verify `ARTIFACT_STORAGE_DIR` and `ARTIFACT_BASE_URL` point to writable volume / CDN |

## 3. Troubleshooting Steps

1. **Check health**: `curl -H "Authorization: Bearer <token>" http://engine/ -v`
2. **Inspect metrics**: `/metrics` exposes latency histogram + quality/uncertainty counters.
3. **Reproduce**: Run `python -m ...eval.evaluate --dataset <manifest>` with the problematic crop.
4. **Logs**: Structured logs include `request_id`, `labels`, `lesion_area_pct`, `counts`, `uncertain`.
5. **Restart**: If checkpoints corrupt, delete `.cache/image_analysis/checkpoints/*` then rerun prefetch script.

## 4. Escalation

- Product owner: Crop Intelligence squad lead
- ML owners: Vision team (contact in Slack `#vision-ml`)

Provide request_id, timestamps, incoming payload metadata (field_id/crop), and artifact URLs when escalating.
