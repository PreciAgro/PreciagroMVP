"""Evaluation script for the Image Analysis Engine."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import yaml

from ..app.models import AnalysisMetadata, ImageAnalysisRequest
from ..app.services.analyzer import ImageAnalysisService


@dataclass
class EvalSample:
    id: str
    crop: str
    disease_code: str
    stage_code: str
    image_base64: str
    quantify_lesions: bool
    count_objects: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Image Analysis Engine on a dataset slice."
    )
    parser.add_argument("--dataset", required=True, help="Path to dataset YAML manifest.")
    parser.add_argument("--metrics-out", help="Optional path to write metrics JSON.")
    parser.add_argument("--max-samples", type=int, help="Limit number of samples evaluated.")
    return parser.parse_args()


def load_dataset(
    path: Path, max_samples: int | None = None
) -> Tuple[Dict[str, Any], List[EvalSample]]:
    data = yaml.safe_load(path.read_text())
    samples_raw = data.get("samples", [])
    if max_samples is not None:
        samples_raw = samples_raw[:max_samples]

    samples = [
        EvalSample(
            id=entry["id"],
            crop=entry["crop"],
            disease_code=entry["label"],
            stage_code=entry["growth_stage"],
            image_base64=entry["image_base64"],
            quantify_lesions=bool(entry.get("quantify_lesions", False)),
            count_objects=bool(entry.get("count_objects", False)),
        )
        for entry in samples_raw
    ]
    return data.get("dataset", {}), samples


def macro_f1(truths: List[str], preds: List[str]) -> float:
    labels = sorted(set(truths) | set(preds))
    if not labels:
        return 0.0
    f1_scores: List[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(truths, preds) if t == label and p == label)
        fp = sum(1 for t, p in zip(truths, preds) if t != label and p == label)
        fn = sum(1 for t, p in zip(truths, preds) if t == label and p != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        f1_scores.append(f1)
    return round(sum(f1_scores) / len(f1_scores), 4)


def stage_accuracy(truths: List[str], preds: List[str]) -> float:
    if not truths:
        return 0.0
    correct = sum(1 for t, p in zip(truths, preds) if t == p)
    return round(correct / len(truths), 4)


def rejection_precision(truths: List[str], preds: List[str], uncertain: List[bool]) -> float:
    uncertain_pairs = [(t, p) for t, p, u in zip(truths, preds, uncertain) if u]
    if not uncertain_pairs:
        return 0.0
    incorrect_uncertain = sum(1 for t, p in uncertain_pairs if t != p)
    return round(incorrect_uncertain / len(uncertain_pairs), 4)


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(values, pct))


def build_request(sample: EvalSample) -> ImageAnalysisRequest:
    meta = AnalysisMetadata(field_id=sample.id)
    return ImageAnalysisRequest(
        crop=sample.crop,
        image_base64=sample.image_base64,
        image_url=None,
        client_request_id=sample.id,
        quantify_lesions=sample.quantify_lesions,
        count_objects=sample.count_objects,
        meta=meta,
    )


def main() -> None:
    args = parse_args()
    dataset_meta, samples = load_dataset(Path(args.dataset), args.max_samples)

    service = ImageAnalysisService()
    disease_truths: List[str] = []
    disease_preds: List[str] = []
    stage_truths: List[str] = []
    stage_preds: List[str] = []
    uncertain_flags: List[bool] = []
    latencies_ms: List[float] = []
    results: List[Dict[str, Any]] = []

    for sample in samples:
        request = build_request(sample)
        start = time.perf_counter()
        response = service.analyze(request)
        duration_ms = (time.perf_counter() - start) * 1000.0
        latencies_ms.append(duration_ms)

        disease_truths.append(sample.disease_code)
        disease_preds.append(response.disease.code)
        stage_truths.append(sample.stage_code)
        stage_preds.append(response.growth_stage.code)
        uncertain_flags.append(not response.quality.passed)

        results.append(
            {
                "id": sample.id,
                "truth": sample.disease_code,
                "prediction": response.disease.code,
                "stage_truth": sample.stage_code,
                "stage_prediction": response.growth_stage.code,
                "health_score": response.health_score,
                "uncertain": not response.quality.passed,
                "latency_ms": duration_ms,
            }
        )

    metrics = {
        "dataset": dataset_meta,
        "disease_macro_f1": macro_f1(disease_truths, disease_preds),
        "stage_accuracy": stage_accuracy(stage_truths, stage_preds),
        "rejection_precision": rejection_precision(disease_truths, disease_preds, uncertain_flags),
        "latency_ms": {
            "mean": round(sum(latencies_ms) / len(latencies_ms), 2) if latencies_ms else 0.0,
            "p95": round(percentile(latencies_ms, 95), 2),
        },
        "samples": results,
    }

    print(json.dumps(metrics, indent=2))  # noqa: T201

    if args.metrics_out:
        out_path = Path(args.metrics_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
