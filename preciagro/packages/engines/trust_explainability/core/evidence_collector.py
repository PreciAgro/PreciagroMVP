"""Evidence Collection and Provenance Module.

Collects evidence from upstream engines with strict data lineage.
Stores references, not copies, to maintain single source of truth.
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..contracts.v1.schemas import EvidenceItem, ExplanationRequest
from ..contracts.v1.enums import EvidenceType

logger = logging.getLogger(__name__)


class EvidenceCollector:
    """Collects and normalizes evidence from upstream engines.

    Maintains strict data lineage - stores references, not copies.
    """

    def __init__(self) -> None:
        """Initialize evidence collector."""
        self._evidence_cache: Dict[str, EvidenceItem] = {}

    def collect(self, request: ExplanationRequest) -> List[EvidenceItem]:
        """Collect all relevant evidence for an explanation request.

        Args:
            request: Explanation request containing context and optional evidence

        Returns:
            List of normalized evidence items
        """
        evidence_items: List[EvidenceItem] = []

        # If evidence is pre-provided, normalize it
        if request.evidence:
            for ev in request.evidence:
                item = self._normalize_evidence(ev)
                if item:
                    evidence_items.append(item)

        # Add model output as evidence
        model_evidence = self._add_model_evidence(
            model_output=request.model_outputs,
            model_id=request.model_id,
            model_type=request.model_type,
        )
        evidence_items.append(model_evidence)

        # Extract context-based evidence
        context_evidence = self._extract_context_evidence(request.context)
        evidence_items.extend(context_evidence)

        # Cache evidence by ID for retrieval
        for item in evidence_items:
            self._evidence_cache[item.id] = item

        logger.info(
            f"Collected {len(evidence_items)} evidence items for request {request.request_id}"
        )
        return evidence_items

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceItem]:
        """Retrieve cached evidence by ID.

        Args:
            evidence_id: Evidence item ID

        Returns:
            EvidenceItem if found, None otherwise
        """
        return self._evidence_cache.get(evidence_id)

    def add_image_evidence(
        self,
        image_id: str,
        source_engine: str = "image_analysis",
        content_ref: Optional[str] = None,
        summary: str = "",
        confidence: float = 1.0,
    ) -> EvidenceItem:
        """Add image evidence with reference.

        Args:
            image_id: Image identifier in source engine
            source_engine: Source engine name
            content_ref: URI reference to image
            summary: Brief summary
            confidence: Evidence quality confidence

        Returns:
            Created EvidenceItem
        """
        item = EvidenceItem(
            evidence_type=EvidenceType.IMAGE,
            source_engine=source_engine,
            source_id=image_id,
            content_ref=content_ref or f"image://{source_engine}/{image_id}",
            summary=summary or f"Image from {source_engine}",
            confidence=confidence,
        )
        self._evidence_cache[item.id] = item
        return item

    def add_sensor_evidence(
        self, sensor_data: Dict[str, Any], sensor_id: str, source_engine: str = "geo_context"
    ) -> EvidenceItem:
        """Add sensor data evidence.

        Args:
            sensor_data: Sensor reading data
            sensor_id: Sensor identifier
            source_engine: Source engine name

        Returns:
            Created EvidenceItem
        """
        # Extract key metrics for summary
        sensor_type = sensor_data.get("type", "unknown")
        value = sensor_data.get("value", "N/A")
        unit = sensor_data.get("unit", "")

        item = EvidenceItem(
            evidence_type=EvidenceType.SENSOR,
            source_engine=source_engine,
            source_id=sensor_id,
            content_ref=f"sensor://{source_engine}/{sensor_id}",
            content_hash=self._compute_hash(sensor_data),
            summary=f"{sensor_type}: {value} {unit}",
            confidence=sensor_data.get("confidence", 0.9),
            metadata={"sensor_data": sensor_data},
        )
        self._evidence_cache[item.id] = item
        return item

    def _add_model_evidence(
        self, model_output: Dict[str, Any], model_id: str, model_type: str
    ) -> EvidenceItem:
        """Create evidence item from model output.

        Args:
            model_output: Model's output dictionary
            model_id: Model identifier
            model_type: Type of model

        Returns:
            Created EvidenceItem
        """
        # Extract key fields for summary
        diagnosis = model_output.get("diagnosis", model_output.get("prediction", "unknown"))
        confidence = model_output.get("confidence", 0.0)

        return EvidenceItem(
            evidence_type=EvidenceType.MODEL_OUTPUT,
            source_engine=f"{model_type}_engine",
            source_id=model_id,
            content_ref=f"model://{model_id}",
            content_hash=self._compute_hash(model_output),
            summary=f"Model {model_id}: {diagnosis} (conf: {confidence:.2f})",
            confidence=confidence,
            metadata={"model_output": model_output, "model_type": model_type},
        )

    def _extract_context_evidence(self, context: Dict[str, Any]) -> List[EvidenceItem]:
        """Extract evidence from request context.

        Args:
            context: Context dictionary

        Returns:
            List of evidence items extracted from context
        """
        items: List[EvidenceItem] = []

        # Weather data
        if "weather" in context:
            weather = context["weather"]
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.WEATHER,
                    source_engine="geo_context",
                    source_id=f"weather_{context.get('region', 'unknown')}",
                    summary=self._format_weather_summary(weather),
                    confidence=0.95,
                    metadata={"weather": weather},
                )
            )

        # Crop information
        if "crop" in context:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.TEXT,
                    source_engine="crop_intelligence",
                    source_id=f"crop_{context['crop']}",
                    summary=f"Crop: {context['crop']}",
                    confidence=1.0,
                    metadata={"crop": context["crop"]},
                )
            )

        # Historical records
        if "history" in context:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.HISTORICAL,
                    source_engine="farmer_profile",
                    source_id=f"history_{context.get('farmer_id', 'unknown')}",
                    summary="Historical farm records",
                    confidence=0.85,
                    metadata={"history": context["history"]},
                )
            )

        return items

    def _normalize_evidence(self, raw: Dict[str, Any]) -> Optional[EvidenceItem]:
        """Normalize raw evidence dictionary to EvidenceItem.

        Args:
            raw: Raw evidence dictionary

        Returns:
            Normalized EvidenceItem or None if invalid
        """
        try:
            # Map string type to enum
            ev_type_str = raw.get("type", raw.get("evidence_type", "text"))
            try:
                ev_type = EvidenceType(ev_type_str.lower())
            except ValueError:
                ev_type = EvidenceType.TEXT

            return EvidenceItem(
                evidence_type=ev_type,
                source_engine=raw.get("source_engine", raw.get("source", "unknown")),
                source_id=raw.get("source_id", raw.get("id", "unknown")),
                content_ref=raw.get("content_ref", raw.get("ref")),
                summary=raw.get("summary", ""),
                confidence=raw.get("confidence", 0.8),
                metadata=raw.get("metadata", {}),
            )
        except Exception as e:
            logger.warning(f"Failed to normalize evidence: {e}")
            return None

    def _format_weather_summary(self, weather: Dict[str, Any]) -> str:
        """Format weather data into brief summary.

        Args:
            weather: Weather data dictionary

        Returns:
            Formatted summary string
        """
        temp = weather.get("temp", weather.get("temperature"))
        humidity = weather.get("humidity")
        rain = weather.get("rainfall", weather.get("rain"))

        parts = []
        if temp is not None:
            parts.append(f"{temp}°C")
        if humidity is not None:
            parts.append(f"{humidity}% humidity")
        if rain is not None:
            parts.append(f"{rain}mm rain")

        return ", ".join(parts) if parts else "Weather data available"

    def _compute_hash(self, data: Any) -> str:
        """Compute SHA-256 hash of data for verification.

        Args:
            data: Data to hash

        Returns:
            Hex-encoded SHA-256 hash
        """
        import json

        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
