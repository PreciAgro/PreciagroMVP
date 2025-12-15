"""Service responsible for orchestrating image analysis requests."""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import cv2
import numpy as np

from ..core import settings
from ..core.registry import CropModelConfig, get_label_registry, get_model_registry
from ..explainability import GradCAMGenerator
from ..counting import CountingEngine
from ..inference import (
    ClassifierHead,
    ClassifierResult,
    ClipFallback,
    PredictedLabel,
)
from ..models import (
    AnalysisMetadata,
    CountsResult,
    DiseasePrediction,
    GrowthStagePrediction,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    ImageQualityResult,
    ResponseExplanations,
)
from ..pipeline import QualityGate, QualityGateResult
from ..segmentation import LesionSegmentation, LesionSegmenter
from ..security import download_image_from_url
from ..storage import ArtifactStorage
from ..telemetry import telemetry
from .scoring import compute_health_score

LOGGER = logging.getLogger(__name__)


@dataclass
class GradcamArtifact:
    """Holds Grad-CAM outputs for downstream consumers."""

    url: Optional[str]
    heatmap: Optional[np.ndarray]


class ImageAnalysisService:
    """Encapsulates request validation, heuristics, and response shaping."""

    def __init__(self) -> None:
        self.model_registry = get_model_registry()
        self.label_registry = get_label_registry()
        self.quality_gate = QualityGate()
        self.classifier_head = ClassifierHead()
        self.clip_fallback = ClipFallback(self.label_registry)
        self.gradcam_generator = GradCAMGenerator()
        self.artifact_storage = ArtifactStorage()
        self.lesion_segmenter = LesionSegmenter()
        self.counting_engine = CountingEngine()

    def analyze(self, payload: ImageAnalysisRequest) -> ImageAnalysisResponse:
        """Run quality, inference, explainability, and optional lesion quantification."""

        start_time = time.perf_counter()
        crop_config = self.model_registry.get_crop(payload.crop)

        image_matrix: Optional[np.ndarray] = None
        try:
            if payload.image_base64:
                image_matrix = self._decode_base64_image(payload.image_base64)
            elif payload.image_url:
                image_matrix = download_image_from_url(payload.image_url)
        except ValueError as exc:
            raise ValueError(f"Image ingestion failed: {exc}") from exc

        if image_matrix is not None:
            quality_result = self.quality_gate.evaluate(image_matrix, crop_config.quality)
        else:
            quality_result = QualityGateResult(
                passed=False,
                notes=["Image could not be loaded for analysis."],
            )

        if not quality_result.passed:
            LOGGER.warning(
                "Quality gate flagged image",
                extra={
                    "crop": payload.crop,
                    "request_id": payload.client_request_id,
                    "quality_notes": quality_result.notes,
                    "quality_metrics": getattr(quality_result, "metrics", {}),
                },
            )
            telemetry.record_quality_failure()

        classifier_result = self.classifier_head.predict(payload, image_matrix, crop_config)
        final_labels = self._apply_clip_fallback(
            image_matrix, payload.crop, crop_config, classifier_result
        )
        disease_prediction = self._build_disease_section(final_labels)
        growth_stage_prediction = self._build_stage_section(payload.crop)
        disease_confidence = final_labels[0].confidence if final_labels else 0.0

        gradcam_artifact = self._maybe_generate_gradcam(
            image_matrix=image_matrix,
            crop_config=crop_config,
            classifier_result=classifier_result,
            payload=payload,
        )

        lesion_result = self._maybe_segment_lesions(
            image_matrix=image_matrix,
            crop_config=crop_config,
            payload=payload,
            heatmap=gradcam_artifact.heatmap if gradcam_artifact else None,
        )

        mask_url: Optional[str] = None
        mask_binary_url: Optional[str] = None
        lesion_pct: Optional[float] = None
        if lesion_result:
            lesion_pct = round(lesion_result.area_ratio, 4)
            mask_url = self.artifact_storage.store_mask_overlay(
                overlay_bgr=lesion_result.overlay_bgr,
                crop=payload.crop or "generic",
                request_id=payload.client_request_id,
            )
            mask_binary_url = self.artifact_storage.store_mask_binary(
                mask=lesion_result.mask,
                crop=payload.crop or "generic",
                request_id=payload.client_request_id,
            )

        health_score = compute_health_score(
            disease_confidence=disease_confidence,
            lesion_pct=lesion_pct,
            quality_passed=quality_result.passed,
        )
        uncertain = disease_confidence < settings.MIN_CONFIDENCE_HEALTHY
        quality_notes = list(quality_result.notes)
        if uncertain:
            quality_notes.append(settings.UNCERTAIN_NOTE)

        counts = self._maybe_count_objects(
            image_matrix=image_matrix,
            crop_config=crop_config,
            payload=payload,
        )

        response = ImageAnalysisResponse(
            crop=payload.crop,
            disease=disease_prediction,
            growth_stage=growth_stage_prediction,
            health_score=health_score,
            lesion_area_pct=lesion_pct,
            counts=counts,
            quality=ImageQualityResult(
                passed=quality_result.passed and not uncertain,
                notes=quality_notes,
            ),
            explanations=ResponseExplanations(
                gradcam_url=gradcam_artifact.url if gradcam_artifact else None,
                mask_url=mask_url,
                mask_binary_url=mask_binary_url,
            ),
            meta=self._normalize_metadata(payload.meta),
        )

        telemetry_status = "ok"
        if not quality_result.passed or uncertain:
            telemetry_status = "uncertain"

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        telemetry.record_latency(duration_ms, telemetry_status)
        if uncertain:
            telemetry.record_uncertain()

        LOGGER.debug(
            "Image analysis response generated",
            extra={
                "crop": payload.crop,
                "health_score": health_score,
                "labels": [label.name for label in final_labels],
                "request_id": payload.client_request_id,
                "classifier_stub": classifier_result.used_stub,
                "lesion_area_pct": lesion_pct,
                "counts": counts.model_dump(),
                "uncertain": uncertain,
                "latency_ms": duration_ms,
            },
        )

        return response

    def _apply_clip_fallback(
        self,
        image_matrix: Optional[np.ndarray],
        crop: str,
        crop_config: CropModelConfig,
        classifier_result: ClassifierResult,
    ) -> List[PredictedLabel]:
        """Apply CLIP fallback when classifier confidence is below the configured threshold."""

        labels = classifier_result.labels
        if not labels:
            LOGGER.warning("Classifier returned no labels; skipping CLIP fallback evaluation")
            return labels

        if (
            not crop_config.clip.enabled
            or classifier_result.top1_confidence >= crop_config.classifier.threshold
            or image_matrix is None
        ):
            return labels

        clip_label = self.clip_fallback.rank(image_matrix, crop, crop_config)
        if not clip_label:
            return labels

        merged = self._merge_labels(clip_label, labels)
        LOGGER.info(
            "CLIP fallback applied",
            extra={
                "crop": crop,
                "classifier_conf": classifier_result.top1_confidence,
                "clip_label": clip_label.name,
                "clip_conf": clip_label.confidence,
            },
        )
        return merged

    def _merge_labels(
        self,
        primary: PredictedLabel,
        existing: List[PredictedLabel],
    ) -> List[PredictedLabel]:
        """Return a deduplicated label list with the primary label first."""

        deduped = [lbl for lbl in existing if lbl.name != primary.name]
        return [primary] + deduped

    def _maybe_generate_gradcam(
        self,
        image_matrix: Optional[np.ndarray],
        crop_config: CropModelConfig,
        classifier_result: ClassifierResult,
        payload: ImageAnalysisRequest,
    ) -> Optional[GradcamArtifact]:
        """Generate Grad-CAM overlay and persist it when explainability is enabled."""

        if (
            not settings.EXPLAINABILITY_ENABLED
            or image_matrix is None
            or not self.gradcam_generator.available
        ):
            return None

        if not classifier_result.labels:
            return None

        target_idx = classifier_result.raw_topk[0][0] if classifier_result.raw_topk else 0

        try:
            bundle = self.classifier_head.get_bundle(crop_config)
            gradcam = self.gradcam_generator.generate(
                bundle=bundle,
                image_bgr=image_matrix,
                target_index=target_idx,
                transform_override=bundle.get("transform"),
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("GradCAM generation failed: %s", exc)
            return None

        if gradcam is None:
            return None

        url = self.artifact_storage.store_heatmap(
            gradcam.overlay_bgr,
            crop=payload.crop or "generic",
            request_id=payload.client_request_id,
        )
        return GradcamArtifact(url=url, heatmap=gradcam.heatmap_gray)

    def _maybe_segment_lesions(
        self,
        image_matrix: Optional[np.ndarray],
        crop_config: CropModelConfig,
        payload: ImageAnalysisRequest,
        heatmap: Optional[np.ndarray],
    ) -> Optional[LesionSegmentation]:
        """Trigger lesion segmentation when enabled by config/request."""

        if (
            image_matrix is None
            or not payload.quantify_lesions
            or not crop_config.segmentation.enabled
        ):
            return None

        try:
            return self.lesion_segmenter.segment(
                image_bgr=image_matrix,
                crop_config=crop_config,
                heatmap=heatmap,
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Lesion segmentation failed: %s", exc)
            return None

    def _maybe_count_objects(
        self,
        image_matrix: Optional[np.ndarray],
        crop_config: CropModelConfig,
        payload: ImageAnalysisRequest,
    ) -> CountsResult:
        """Run YOLO counting when enabled."""

        counts = CountsResult()
        if image_matrix is None or not payload.count_objects or not crop_config.counting.enabled:
            return counts

        result = self.counting_engine.count(image_matrix, crop_config)
        if "fruit" in result.counts:
            counts.fruit = result.counts["fruit"]
        if "pest" in result.counts:
            counts.pest = result.counts["pest"]

        LOGGER.debug(
            "Counting results",
            extra={
                "counts": result.counts,
                "counting_stub": result.used_stub,
                "counting_model": result.model_version,
            },
        )
        return counts

    def _build_disease_section(self, labels: List[PredictedLabel]) -> DiseasePrediction:
        """Convert diagnosis output to the standardized response block."""

        if labels:
            top_label = labels[0]
            code = self.label_registry.disease_code_for(top_label.name)
            return DiseasePrediction(code=code, label=top_label.name, conf=top_label.confidence)

        LOGGER.warning("Classifier returned no labels; defaulting to UNKNOWN")
        return DiseasePrediction(code="CIE.DZ.UNKNOWN", label="unknown", conf=0.0)

    def _build_stage_section(self, crop: str) -> GrowthStagePrediction:
        """Provide a naive growth-stage guess until models are integrated."""

        stage = self.label_registry.growth_stage_for_crop(crop.lower())
        if stage:
            return GrowthStagePrediction(code=stage.code, label=stage.label, conf=0.7)
        return GrowthStagePrediction(code="STAGE.UNKNOWN", label="unknown", conf=0.4)

    def _normalize_metadata(self, metadata: AnalysisMetadata | None) -> AnalysisMetadata:
        """Ensure metadata defaults are applied."""

        if metadata is None:
            return AnalysisMetadata(captured_at=datetime.utcnow())

        if metadata.captured_at is None:
            return metadata.model_copy(update={"captured_at": datetime.utcnow()})

        return metadata

    def _decode_base64_image(self, image_base64: str) -> Optional[np.ndarray]:
        """Decode a base64 string into an OpenCV image matrix."""

        try:
            binary = base64.b64decode(image_base64, validate=True)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to decode base64 image: %s", exc)
            return None

        np_buffer = np.frombuffer(binary, dtype=np.uint8)
        image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
        if image is None:
            LOGGER.warning("cv2.imdecode returned None for provided image payload")
        return image
