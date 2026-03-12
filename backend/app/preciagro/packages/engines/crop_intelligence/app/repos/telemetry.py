from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.schemas import TelemetryBatch, WeatherPoint, VIPoint, SoilBaseline
from ..db import models


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


class TelemetryRepository:
    """Persists telemetry inputs (weather, VI, soil baselines)."""

    def __init__(self, session: Session):
        self.session = session

    def record_batch(self, batch: TelemetryBatch) -> None:
        if batch.weather:
            for point in batch.weather:
                self._store_weather(batch.field_id, point)
        if batch.vi:
            for vi in batch.vi:
                self._store_vi(batch.field_id, vi)
        if batch.soil:
            self.add_soil_baseline(batch.field_id, batch.soil)

    def _store_weather(self, field_id: str, point: WeatherPoint) -> None:
        record = models.TelemetryWeather(
            field_id=field_id,
            ts=_parse_ts(point.ts),
            tmax_c=point.tmax,
            tmin_c=point.tmin,
            rh_mean=point.rh,
            rain_mm=point.rain,
            wind_ms=point.wind,
            radiation_mjm2=point.rad,
            source="ingest",
            quality="good",
        )
        self.session.add(record)

    def _store_vi(self, field_id: str, point: VIPoint) -> None:
        record = models.TelemetryVI(
            field_id=field_id,
            date=_parse_date(point.date),
            ndvi=point.ndvi,
            evi=point.evi,
            source="ingest",
            quality=point.quality,
        )
        self.session.add(record)

    def _store_soil(self, field_id: str, soil: SoilBaseline) -> None:
        record = models.SoilBaseline(
            field_id=field_id,
            source=soil.src,
            texture=soil.texture,
            whc_mm=soil.whc_mm,
            uncertainty=soil.uncertainty,
        )
        self.session.add(record)

    def add_soil_baseline(self, field_id: str, soil: SoilBaseline) -> None:
        """Public helper so integrations can insert soil snapshots."""
        self._store_soil(field_id, soil)
        self.session.flush()

    def season_summary(self, field_id: str) -> dict:
        rain_stmt = select(func.coalesce(func.sum(models.TelemetryWeather.rain_mm), 0.0)).where(
            models.TelemetryWeather.field_id == field_id
        )
        rain_total = float(self.session.execute(rain_stmt).scalar_one())
        return {"cumulative_rain_mm": rain_total}
