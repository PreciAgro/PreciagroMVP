from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.config import settings
from ..models.schemas import FieldRegister, SoilBaseline
from ..repos.telemetry import TelemetryRepository
from ..db import models
from .geocontext import GeoContextClient
from .data_integration import DataIntegrationClient
from .temporal_logic import TemporalLogicClient
from .image_analysis import ImageAnalysisClient


@dataclass
class IntegrationHub:
    geocontext: GeoContextClient
    data_integration: DataIntegrationClient
    temporal: TemporalLogicClient
    image_analysis: ImageAnalysisClient

    def ensure_soil_baseline(self, repo: TelemetryRepository, field: models.Field) -> None:
        if not settings.GEOCONTEXT_BASE_URL:
            return
        soil = repo.session.query(models.SoilBaseline).filter_by(field_id=field.field_id).first()
        if soil:
            return
        response = self.geocontext.fetch_soil(field.field_id, field.boundary_geojson)
        if not response:
            return
        baseline = SoilBaseline(
            src=response.get("source", "geocontext"),
            texture=response.get("texture"),
            whc_mm=response.get("whc_mm"),
            uncertainty=response.get("uncertainty"),
        )
        repo.add_soil_baseline(field.field_id, baseline)

    def fetch_schedule(self, field_id: str) -> Optional[dict]:
        if not settings.TEMPORAL_LOGIC_BASE_URL:
            return None
        return self.temporal.fetch_schedule(field_id)


integration_hub = IntegrationHub(
    geocontext=GeoContextClient(settings.GEOCONTEXT_BASE_URL),
    data_integration=DataIntegrationClient(settings.DATA_INTEGRATION_BASE_URL),
    temporal=TemporalLogicClient(settings.TEMPORAL_LOGIC_BASE_URL),
    image_analysis=ImageAnalysisClient(settings.IMAGE_ANALYSIS_BASE_URL),
)
