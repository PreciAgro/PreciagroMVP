# Image Analysis Engine

Pretrained-first FastAPI service that ingests crop photos, runs a quality gate, classifies disease and growth-stage signals, and emits the standard JSON response consumed by Crop Intelligence, Temporal Logic, GeoContext, and Data Integration engines.

## Runtime Modes (CPU vs GPU)

- The service defaults to CPU execution. Torch/timm and CLIP fallbacks automatically use `cpu` unless a CUDA or Apple MPS device is detected.
- GPU acceleration is optional but recommended for high-throughput segmentation/counting. When `torch.cuda.is_available()` returns true, both the classifier head and CLIP fallback move models onto the GPU automatically.
- Quality-gate heuristics (OpenCV) remain on CPU regardless of GPU availability to avoid PCIe transfer overhead.

## Fine-Tuned Weights & Config Registry

- `config/models.yaml` is the single source of truth for crop-specific backbones, thresholds, and optional heads (segmentation/counting).
- Each crop entry accepts a `weights_path`:
  - **Local path** (e.g., `/models/maize/efficientnet.pt`) - mount the directory into the container; the loader will `torch.load` the checkpoint.
  - **Remote URI** (`az://`, `s3://`, `gs://`) - used to signal that weights are managed outside the container. The current build logs a warning and keeps the pretrained weights; plug in a blob-download routine before production.
- To add new fine-tuned checkpoints, drop the file in your preferred storage, update `weights_path`, and redeploy. No code changes are required for additional crops or backbones so long as timm supports the model name.

## Pipeline Summary

1. **Quality Gate**: Laplacian blur, exposure histogram, resolution, and center-focus checks with actionable retake guidance, logged to downstream analytics. Thresholds are configurable per crop.
2. **Classifier Head**: Timm backbone (EfficientNetV2, ConvNeXt, EfficientNet-B3, etc.) with optional horizontal-flip TTA. Predictions are cached per `(model_name, weights)` to keep cold-start costs low.
3. **CLIP Fallback (T5)**: When classifier confidence drops below the configured threshold, CLIP ViT models compare the frame to curated prompts under `config/prompts/<crop>.json`. The winner can override the final label so users still get guidance instead of "uncertain".
4. **Explainability (T6)**: Grad-CAM overlays are generated (if torch is available) and stored under `reports/image_analysis/artifacts/<crop>/`, with URLs surfaced in `response.explanations.gradcam_url`. Toggle via `IMAGE_ANALYSIS_EXPLAINABILITY_ENABLED`.
5. **Lesion Quantification (T7)**: When `segmentation.enabled` is true and the request sets `quantify_lesions=true`, a SAM2 predictor (or saliency fallback) produces a binary lesion mask, persists both the overlay and raw binary PNG, and reports `lesion_area_pct`.
6. **Object Counting (T8)**: When `counting.enabled` is true and the request sets `count_objects=true`, a YOLOv8 head counts configured classes (fruit/pest) and logs the result in `response.counts`.
7. **Output Aggregation (T9)**: `health_score` blends classifier confidence, lesion coverage, and quality gate status. If the top prediction confidence drops below `IMAGE_ANALYSIS_MIN_CONFIDENCE_HEALTHY` the response marks `quality.passed=false` and adds a retake note so downstream engines know the diagnosis is uncertain.
8. **Integration Adapters (T10)**: `app/integrations/adapters.py` exposes helper functions that shape `ImageAnalysisResponse` into the payloads expected by Crop Intelligence, Temporal Logic, GeoContext, and Data Integration engines (with artifact URLs preserved for downstream storage).
9. **Future Heads**: Additional YOLO and SAM2 enhancements share the same registry via the `counting` or `segmentation` blocks.

## Local Development

```bash
pip install -r preciagro/packages/engines/image_analysis/requirements.txt
uvicorn preciagro.packages.engines.image_analysis.app.main:app --reload --port 8084
```

- To exercise GPU inference locally, install the CUDA-enabled PyTorch wheel before installing the engine requirements.
- Provide environment overrides via `IMAGE_ANALYSIS_*` (see `config.py`). For example `IMAGE_ANALYSIS_API_PREFIX=/api/image-analysis`.
- Explainability and segmentation artifacts default to the local `reports/image_analysis/artifacts` directory; to expose them externally set `IMAGE_ANALYSIS_ARTIFACT_BASE_URL=https://cdn.example.com/ia-artifacts`.

## Testing

The test suite lives under `preciagro/packages/engines/image_analysis/tests`. Run it via the repository root:

```bash
pytest preciagro/packages/engines/image_analysis/tests -q
```

Classifier tests mock timm/torch so they run quickly without the heavy dependencies. Add similar stubs when introducing SAM, YOLO, or CLIP unit tests.

## API

- `POST /api/image-analysis/analyze-image` – single-image analysis.
- `POST /api/image-analysis/batch` – accepts up to `IMAGE_ANALYSIS_MAX_BATCH_ITEMS` requests per payload and returns an ordered list of responses. Use this for burst uploads (e.g., drone frames).

All endpoints sit behind the API Gateway and inherit its JWT/rate-limit enforcement. The batch handler also performs server-side validation and will respond with HTTP 400 if the payload exceeds size or count limits.

## Security & Compliance

- JWT validation is enforced via the shared security dependency (`get_tenant_context`). Set `JWT_PUBKEY` in the environment (or enable `DEV_MODE=true` for local testing).
- Direct uploads are capped by `IMAGE_ANALYSIS_MAX_BASE64_BYTES` to avoid runaway payloads, and remote ingestion requires signed https URLs whose hosts appear in `IMAGE_ANALYSIS_ALLOWED_IMAGE_HOSTS`.
- Remote images are downloaded with bounded timeouts/size limits, decoded in-memory, and never persisted to disk. Raw artifacts (Grad-CAM overlays, lesion masks) go to `reports/image_analysis/artifacts`, which can be scoped per tenant when wiring up object storage.

## Further Reading

- `docs/engines/image_analysis.md` – architecture, evaluation flow, release checklist.
- `preciagro/packages/engines/image_analysis/RUNBOOK.md` – incident response steps and escalation paths.
