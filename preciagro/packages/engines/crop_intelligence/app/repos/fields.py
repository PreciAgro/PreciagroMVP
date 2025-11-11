from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.schemas import FieldRegister
from ..db import models


def _to_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class FieldRepository:
    """Persistence helpers for CIE field metadata."""

    def __init__(self, session: Session):
        self.session = session

    def upsert(self, payload: FieldRegister) -> models.Field:
        planting = _to_date(payload.planting_date)
        now = datetime.utcnow()

        field = self.session.get(models.Field, payload.field_id)
        if field:
            field.boundary_geojson = payload.boundary_geojson
            field.crop = payload.crop
            field.planting_date = planting
            field.irrigation_access = payload.irrigation_access
            field.target_yield_band = payload.target_yield_band
            field.budget_class = payload.budget_class
            field.updated_at = now
        else:
            field = models.Field(
                field_id=payload.field_id,
                boundary_geojson=payload.boundary_geojson,
                crop=payload.crop,
                planting_date=planting,
                irrigation_access=payload.irrigation_access,
                target_yield_band=payload.target_yield_band,
                budget_class=payload.budget_class,
                status="active",
                created_at=now,
                updated_at=now,
            )
            self.session.add(field)

        self.session.flush()
        return field

    def get(self, field_id: str) -> Optional[models.Field]:
        return self.session.get(models.Field, field_id)

    def latest_soil_whc(self, field_id: str) -> Optional[float]:
        stmt = (
            select(models.SoilBaseline.whc_mm)
            .where(models.SoilBaseline.field_id == field_id)
            .order_by(models.SoilBaseline.recorded_at.desc())
        )
        result = self.session.execute(stmt).scalars().first()
        return result
