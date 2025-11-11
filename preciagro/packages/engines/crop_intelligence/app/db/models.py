from __future__ import annotations

import uuid
from datetime import datetime, date

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from ..core.config import settings


# Use JSONB on PostgreSQL and generic JSON elsewhere (e.g., SQLite for tests)
if settings.DATABASE_URL.lower().startswith("postgresql"):
    JSONType = postgresql.JSONB
else:
    JSONType = sa.JSON


class Field(Base):
    __tablename__ = "cie_fields"

    field_id: Mapped[str] = mapped_column(sa.String(100), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    boundary_geojson: Mapped[dict] = mapped_column(JSONType, nullable=False)
    area_ha: Mapped[float | None] = mapped_column(sa.Float)
    crop: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    planting_date: Mapped[date | None] = mapped_column(sa.Date)
    harvest_date: Mapped[date | None] = mapped_column(sa.Date)
    irrigation_access: Mapped[str | None] = mapped_column(sa.String(20))
    target_yield_band: Mapped[str | None] = mapped_column(sa.String(50))
    budget_class: Mapped[str] = mapped_column(sa.String(20), default="medium")
    region: Mapped[str | None] = mapped_column(sa.String(100))
    farmer_id: Mapped[str | None] = mapped_column(sa.String(100))
    status: Mapped[str] = mapped_column(sa.String(20), default="active")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)


class SoilBaseline(Base):
    __tablename__ = "cie_soil_baseline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    field_id: Mapped[str] = mapped_column(
        sa.String(100), sa.ForeignKey("cie_fields.field_id", ondelete="CASCADE"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)
    source: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    texture: Mapped[str | None] = mapped_column(sa.String(50))
    whc_mm: Mapped[float | None] = mapped_column(sa.Float)
    ph: Mapped[float | None] = mapped_column(sa.Float)
    organic_matter_pct: Mapped[float | None] = mapped_column(sa.Float)
    nitrogen_ppm: Mapped[float | None] = mapped_column(sa.Float)
    phosphorus_ppm: Mapped[float | None] = mapped_column(sa.Float)
    potassium_ppm: Mapped[float | None] = mapped_column(sa.Float)
    uncertainty: Mapped[str | None] = mapped_column(sa.String(20))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)


class TelemetryWeather(Base):
    __tablename__ = "cie_telemetry_weather"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    field_id: Mapped[str] = mapped_column(
        sa.String(100), sa.ForeignKey("cie_fields.field_id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(sa.DateTime, nullable=False)
    tmax_c: Mapped[float | None] = mapped_column(sa.Float)
    tmin_c: Mapped[float | None] = mapped_column(sa.Float)
    tmean_c: Mapped[float | None] = mapped_column(sa.Float)
    rh_mean: Mapped[float | None] = mapped_column(sa.Float)
    rain_mm: Mapped[float | None] = mapped_column(sa.Float)
    wind_ms: Mapped[float | None] = mapped_column(sa.Float)
    radiation_mjm2: Mapped[float | None] = mapped_column(sa.Float)
    source: Mapped[str | None] = mapped_column(sa.String(50))
    quality: Mapped[str | None] = mapped_column(sa.String(20))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)


class TelemetryVI(Base):
    __tablename__ = "cie_telemetry_vi"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    field_id: Mapped[str] = mapped_column(
        sa.String(100), sa.ForeignKey("cie_fields.field_id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    ndvi: Mapped[float | None] = mapped_column(sa.Float)
    evi: Mapped[float | None] = mapped_column(sa.Float)
    ndwi: Mapped[float | None] = mapped_column(sa.Float)
    source: Mapped[str | None] = mapped_column(sa.String(50))
    quality: Mapped[str | None] = mapped_column(sa.String(20))
    cloud_cover_pct: Mapped[float | None] = mapped_column(sa.Float)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)


class CropType(Base):
    __tablename__ = "cie_crop_types"

    crop_code: Mapped[str] = mapped_column(sa.String(60), primary_key=True)
    display_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    region_tags: Mapped[list[str] | None] = mapped_column(JSONType)
    maturity_class: Mapped[str | None] = mapped_column(sa.String(40))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class GrowthStage(Base):
    __tablename__ = "cie_growth_stages"
    __table_args__ = (sa.UniqueConstraint("crop_code", "stage_code", name="uix_crop_stage_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop_code: Mapped[str] = mapped_column(sa.String(60), sa.ForeignKey("cie_crop_types.crop_code"), nullable=False)
    stage_code: Mapped[str] = mapped_column(sa.String(60), nullable=False)
    display_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    order_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    gdd_min: Mapped[float | None] = mapped_column(sa.Float)
    gdd_max: Mapped[float | None] = mapped_column(sa.Float)
    duration_days: Mapped[int | None] = mapped_column(sa.Integer)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)


class StageRequirement(Base):
    __tablename__ = "cie_stage_requirements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stage_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("cie_growth_stages.id", ondelete="CASCADE"), nullable=False
    )
    requirement_type: Mapped[str] = mapped_column(sa.String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)


class ManagementTemplate(Base):
    __tablename__ = "cie_management_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop_code: Mapped[str] = mapped_column(sa.String(60), sa.ForeignKey("cie_crop_types.crop_code"), nullable=False)
    template_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    sequence: Mapped[dict] = mapped_column(JSONType, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)


class FieldState(Base):
    __tablename__ = "cie_field_state"

    field_id: Mapped[str] = mapped_column(
        sa.String(100), sa.ForeignKey("cie_fields.field_id", ondelete="CASCADE"), primary_key=True
    )
    stage_code: Mapped[str | None] = mapped_column(sa.String(60))
    stage_confidence: Mapped[float] = mapped_column(sa.Float, default=0.0)
    vigor_trend: Mapped[str | None] = mapped_column(sa.String(20))
    risks: Mapped[dict | None] = mapped_column(JSONType)
    last_telemetry_ts: Mapped[datetime | None] = mapped_column(sa.DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Recommendation(Base):
    __tablename__ = "cie_recommendations"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        sa.String(100), sa.ForeignKey("cie_fields.field_id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    stage_code: Mapped[str | None] = mapped_column(sa.String(60))
    source: Mapped[str] = mapped_column(sa.String(40), nullable=False)
    impact_score: Mapped[float | None] = mapped_column(sa.Float)
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)


class ActionFeedback(Base):
    __tablename__ = "cie_action_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recommendation_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("cie_recommendations.id", ondelete="SET NULL")
    )
    field_id: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    action_id: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    decision: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(sa.Text)
    recorded_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)


class ModelRegistry(Base):
    __tablename__ = "cie_model_registry"
    __table_args__ = (sa.UniqueConstraint("model_name", "crop_code", "region", name="uix_model_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    version: Mapped[str] = mapped_column(sa.String(40), nullable=False)
    crop_code: Mapped[str | None] = mapped_column(sa.String(60))
    region: Mapped[str | None] = mapped_column(sa.String(80))
    artifact_uri: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    checksum: Mapped[str | None] = mapped_column(sa.String(64))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)


class StageEvidence(Base):
    __tablename__ = "cie_stage_evidence"
    __table_args__ = (sa.Index("idx_stage_evidence_field", "field_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    field_id: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    stage_code: Mapped[str | None] = mapped_column(sa.String(60))
    evidence_source: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    score: Mapped[float | None] = mapped_column(sa.Float)
    payload: Mapped[dict | None] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)
