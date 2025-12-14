"""
Alembic migration: CIE Schema v1.1 - Ontology and state tables
Revision ID: cie_v1_1_ontology
Revises: cie_v1_0_core_tables
Create Date: 2025-10-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime


revision = "cie_v1_1_ontology"
down_revision = "cie_v1_0_core_tables"
branch_labels = None
depends_on = None

JSONType = getattr(postgresql, "JSONB", sa.JSON)


def upgrade() -> None:
    op.create_table(
        "cie_crop_types",
        sa.Column("crop_code", sa.String(60), primary_key=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("region_tags", JSONType, nullable=True),
        sa.Column("maturity_class", sa.String(40), nullable=True),
        sa.Column("metadata", JSONType, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
        ),
    )

    op.create_table(
        "cie_growth_stages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("crop_code", sa.String(60), sa.ForeignKey("cie_crop_types.crop_code"), nullable=False),
        sa.Column("stage_code", sa.String(60), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("gdd_min", sa.Float, nullable=True),
        sa.Column("gdd_max", sa.Float, nullable=True),
        sa.Column("duration_days", sa.Integer, nullable=True),
        sa.Column("metadata", JSONType, nullable=True),
        sa.UniqueConstraint("crop_code", "stage_code", name="uix_crop_stage_code"),
    )

    op.create_table(
        "cie_stage_requirements",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "stage_id",
            sa.Integer,
            sa.ForeignKey("cie_growth_stages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_type", sa.String(40), nullable=False),
        sa.Column("payload", JSONType, nullable=False),
    )

    op.create_table(
        "cie_management_templates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "crop_code",
            sa.String(60),
            sa.ForeignKey("cie_crop_types.crop_code"),
            nullable=False,
        ),
        sa.Column("template_name", sa.String(120), nullable=False),
        sa.Column("sequence", JSONType, nullable=False),
        sa.Column("metadata", JSONType, nullable=True),
    )

    op.create_table(
        "cie_field_state",
        sa.Column(
            "field_id",
            sa.String(100),
            sa.ForeignKey("cie_fields.field_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("stage_code", sa.String(60), nullable=True),
        sa.Column("stage_confidence", sa.Float, nullable=False, default=0.0),
        sa.Column("vigor_trend", sa.String(20), nullable=True),
        sa.Column("risks", JSONType, nullable=True),
        sa.Column("last_telemetry_ts", sa.DateTime, nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
        ),
    )

    op.create_table(
        "cie_model_registry",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("model_name", sa.String(80), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("crop_code", sa.String(60), nullable=True),
        sa.Column("region", sa.String(80), nullable=True),
        sa.Column("artifact_uri", sa.String(255), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("metadata", JSONType, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.UniqueConstraint("model_name", "crop_code", "region", name="uix_model_scope"),
    )

    op.create_table(
        "cie_recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "field_id",
            sa.String(100),
            sa.ForeignKey("cie_fields.field_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("payload", JSONType, nullable=False),
        sa.Column("stage_code", sa.String(60), nullable=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("impact_score", sa.Float, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=datetime.utcnow),
    )

    op.create_table(
        "cie_action_feedback",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "recommendation_id",
            sa.String(36),
            sa.ForeignKey("cie_recommendations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("field_id", sa.String(100), nullable=False),
        sa.Column("action_id", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("metadata", JSONType, nullable=True),
        sa.Column("recorded_at", sa.DateTime, nullable=False, default=datetime.utcnow),
    )

    op.create_table(
        "cie_stage_evidence",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("field_id", sa.String(100), nullable=False),
        sa.Column("stage_code", sa.String(60), nullable=True),
        sa.Column("evidence_source", sa.String(30), nullable=False),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("payload", JSONType, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=datetime.utcnow),
    )
    op.create_index("idx_stage_evidence_field", "cie_stage_evidence", ["field_id"])


def downgrade() -> None:
    op.drop_index("idx_stage_evidence_field", table_name="cie_stage_evidence")
    op.drop_table("cie_stage_evidence")
    op.drop_table("cie_action_feedback")
    op.drop_table("cie_recommendations")
    op.drop_table("cie_model_registry")
    op.drop_table("cie_field_state")
    op.drop_table("cie_management_templates")
    op.drop_table("cie_stage_requirements")
    op.drop_table("cie_growth_stages")
    op.drop_table("cie_crop_types")
