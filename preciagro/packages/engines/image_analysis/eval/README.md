## Image Analysis Evaluation

This folder contains dataset manifests and scripts that measure backbone quality before promotions.

### Datasets

- `datasets/sample_maize.yaml` – tiny slice (2 samples) meant to verify the tooling locally. Real slices should live in a secure bucket or be generated from tagged datasets exported by Data Integration.

Dataset manifest schema:

```yaml
dataset:
  name: str
  description: str
samples:
  - id: str
    crop: str
    label: CIE disease code (e.g., CIE.DZ.GRAY_LEAF_SPOT)
    growth_stage: stage code (e.g., STAGE.VEGETATIVE)
    image_base64: base64-encoded PNG/JPEG
    quantify_lesions: bool
    count_objects: bool
```

### Running evaluation

```bash
python -m preciagro.packages.engines.image_analysis.eval.evaluate \
  --dataset preciagro/packages/engines/image_analysis/eval/datasets/sample_maize.yaml \
  --metrics-out reports/image_analysis/eval/sample_maize.json
```

Outputs:

- Disease macro F1 (over codes in the manifest)
- Growth stage accuracy
- Rejection precision (how often uncertain predictions were incorrect)
- Latency statistics (mean / p95 in ms)
- Raw predictions for audit
