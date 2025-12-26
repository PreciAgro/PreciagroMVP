"""
Alembic migration: CIE Schema v1.0 - Core tables for persistence
Revision ID: cie_v1_0_core_tables
Revises: 
Create Date: 2025-10-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'cie_v1_0_core_tables'
down_revision = None  # First CIE migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create CIE core schema tables."""

    # ============================================
    # 1. Fields Table
    # ============================================
    op.create_table(
        'cie_fields',
        sa.Column('field_id', sa.String(100), primary_key=True),
        sa.Column('created_at', sa.DateTime,
                  nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, nullable=False,
                  default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('boundary_geojson', JSONB, nullable=False),
        sa.Column('area_ha', sa.Float, nullable=True),
        sa.Column('crop', sa.String(50), nullable=False),
        sa.Column('planting_date', sa.Date, nullable=False),
        sa.Column('harvest_date', sa.Date, nullable=True),
        sa.Column('irrigation_access', sa.String(20), nullable=True),
        sa.Column('target_yield_band', sa.String(50), nullable=True),
        sa.Column('budget_class', sa.String(20),
                  nullable=False, default='medium'),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('farmer_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False,
                  default='active'),  # active, archived, completed
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_fields_crop', 'cie_fields', ['crop'])
    op.create_index('idx_cie_fields_region', 'cie_fields', ['region'])
    op.create_index('idx_cie_fields_status', 'cie_fields', ['status'])
    op.create_index('idx_cie_fields_planting_date',
                    'cie_fields', ['planting_date'])

    # ============================================
    # 2. Soil Baseline Table
    # ============================================
    op.create_table(
        'cie_soil_baseline',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('field_id', sa.String(100), sa.ForeignKey(
            'cie_fields.field_id', ondelete='CASCADE'), nullable=False),
        sa.Column('recorded_at', sa.DateTime,
                  nullable=False, default=datetime.utcnow),
        # soilgrids, lab, farmer_estimate
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('texture', sa.String(50), nullable=True),
        sa.Column('whc_mm', sa.Float, nullable=True),
        sa.Column('ph', sa.Float, nullable=True),
        sa.Column('organic_matter_pct', sa.Float, nullable=True),
        sa.Column('nitrogen_ppm', sa.Float, nullable=True),
        sa.Column('phosphorus_ppm', sa.Float, nullable=True),
        sa.Column('potassium_ppm', sa.Float, nullable=True),
        sa.Column('uncertainty', sa.String(20), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_soil_field_id', 'cie_soil_baseline', ['field_id'])
    op.create_index('idx_cie_soil_recorded_at',
                    'cie_soil_baseline', ['recorded_at'])

    # ============================================
    # 3. Telemetry - Weather Table
    # ============================================
    op.create_table(
        'cie_telemetry_weather',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('field_id', sa.String(100), sa.ForeignKey(
            'cie_fields.field_id', ondelete='CASCADE'), nullable=False),
        sa.Column('ts', sa.DateTime, nullable=False),
        sa.Column('tmax_c', sa.Float, nullable=True),
        sa.Column('tmin_c', sa.Float, nullable=True),
        sa.Column('tmean_c', sa.Float, nullable=True),
        sa.Column('rh_mean', sa.Float, nullable=True),
        sa.Column('rain_mm', sa.Float, nullable=True),
        sa.Column('wind_ms', sa.Float, nullable=True),
        sa.Column('radiation_mjm2', sa.Float, nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('quality', sa.String(20), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_weather_field_ts',
                    'cie_telemetry_weather', ['field_id', 'ts'])
    op.create_index('idx_cie_weather_ts', 'cie_telemetry_weather', ['ts'])

    # ============================================
    # 4. Telemetry - Vegetation Index (VI) Table
    # ============================================
    op.create_table(
        'cie_telemetry_vi',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('field_id', sa.String(100), sa.ForeignKey(
            'cie_fields.field_id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('ndvi', sa.Float, nullable=True),
        sa.Column('evi', sa.Float, nullable=True),
        sa.Column('ndwi', sa.Float, nullable=True),
        # sentinel2, landsat, drone
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('quality', sa.String(20), nullable=True),  # good, fair, poor
        sa.Column('cloud_cover_pct', sa.Float, nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_vi_field_date',
                    'cie_telemetry_vi', ['field_id', 'date'])
    op.create_index('idx_cie_vi_date', 'cie_telemetry_vi', ['date'])

    # ============================================
    # 5. Photos Table
    # ============================================
    op.create_table(
        'cie_photos',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('field_id', sa.String(100), sa.ForeignKey(
            'cie_fields.field_id', ondelete='CASCADE'), nullable=False),
        sa.Column('photo_date', sa.Date, nullable=False),
        sa.Column('uploaded_at', sa.DateTime,
                  nullable=False, default=datetime.utcnow),
        sa.Column('stage_observed', sa.String(50), nullable=True),
        sa.Column('stage_predicted', sa.String(50), nullable=True),
        sa.Column('stage_match', sa.Boolean,
                  nullable=True),  # Ground truth check
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('quality', sa.String(20), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_photos_field_date',
                    'cie_photos', ['field_id', 'photo_date'])
    op.create_index('idx_cie_photos_uploaded_at',
                    'cie_photos', ['uploaded_at'])

    # ============================================
    # 6. Actions Recommended Table
    # ============================================
    op.create_table(
        'cie_actions_recommended',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('action_id', sa.String(100), unique=True, nullable=False),
        sa.Column('field_id', sa.String(100), sa.ForeignKey(
            'cie_fields.field_id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime,
                  nullable=False, default=datetime.utcnow),
        # nitrogen, water, disease, photo_prompt
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('priority_score', sa.Float, nullable=False),
        sa.Column('confidence_overall', sa.Float, nullable=True),
        sa.Column('confidence_breakdown', JSONB, nullable=True),
        sa.Column('recommendation_text', sa.Text, nullable=False),
        sa.Column('timing_window_start', sa.Date, nullable=True),
        sa.Column('timing_window_end', sa.Date, nullable=True),
        sa.Column('budget_class', sa.String(20), nullable=True),
        sa.Column('displayed', sa.Boolean, nullable=False, default=True),
        sa.Column('policy_version', sa.String(20), nullable=True),
        sa.Column('model_version', sa.String(20), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_actions_action_id',
                    'cie_actions_recommended', ['action_id'])
    op.create_index('idx_cie_actions_field_created',
                    'cie_actions_recommended', ['field_id', 'created_at'])
    op.create_index('idx_cie_actions_type',
                    'cie_actions_recommended', ['action_type'])

    # ============================================
    # 7. Actions User Response Table
    # ============================================
    op.create_table(
        'cie_actions_user_response',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('action_id', sa.String(100), sa.ForeignKey(
            'cie_actions_recommended.action_id', ondelete='CASCADE'), nullable=False),
        sa.Column('field_id', sa.String(100), sa.ForeignKey(
            'cie_fields.field_id', ondelete='CASCADE'), nullable=False),
        sa.Column('responded_at', sa.DateTime,
                  nullable=False, default=datetime.utcnow),
        # accepted, rejected, ignored
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('note', sa.Text, nullable=True),
        # When they actually did it
        sa.Column('executed_date', sa.Date, nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_response_action_id',
                    'cie_actions_user_response', ['action_id'])
    op.create_index('idx_cie_response_field_responded',
                    'cie_actions_user_response', ['field_id', 'responded_at'])
    op.create_index('idx_cie_response_decision',
                    'cie_actions_user_response', ['decision'])

    # ============================================
    # 8. Harvest Outcomes Table
    # ============================================
    op.create_table(
        'cie_harvest_outcomes',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('field_id', sa.String(100), sa.ForeignKey(
            'cie_fields.field_id', ondelete='CASCADE'), nullable=False),
        sa.Column('harvest_date', sa.Date, nullable=False),
        sa.Column('recorded_at', sa.DateTime,
                  nullable=False, default=datetime.utcnow),
        sa.Column('yield_t_ha', sa.Float, nullable=True),
        sa.Column('quality_grade', sa.String(20), nullable=True),
        sa.Column('revenue_usd_ha', sa.Float, nullable=True),
        sa.Column('cost_usd_ha', sa.Float, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_harvest_field_id',
                    'cie_harvest_outcomes', ['field_id'])
    op.create_index('idx_cie_harvest_date',
                    'cie_harvest_outcomes', ['harvest_date'])

    # ============================================
    # 9. Event Log Table (append-only audit trail)
    # ============================================
    op.create_table(
        'cie_event_log',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('event_id', UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('timestamp', sa.DateTime,
                  nullable=False, default=datetime.utcnow),
        sa.Column('field_id', sa.String(100), nullable=True),
        # stage_detected, action_recommended, user_feedback, etc.
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('source_engine', sa.String(50),
                  nullable=False, default='cie'),
        sa.Column('policy_version', sa.String(20), nullable=True),
        sa.Column('model_version', sa.String(20), nullable=True),
        sa.Column('schema_version', sa.String(20),
                  nullable=False, default='1.0.0'),
        sa.Column('payload', JSONB, nullable=False),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_cie_events_timestamp', 'cie_event_log', ['timestamp'])
    op.create_index('idx_cie_events_field_id', 'cie_event_log', ['field_id'])
    op.create_index('idx_cie_events_type', 'cie_event_log', ['event_type'])
    op.create_index('idx_cie_events_policy_version',
                    'cie_event_log', ['policy_version'])

    # ============================================
    # 10. Metrics Summary Table (optional - for pre-aggregated metrics)
    # ============================================
    op.create_table(
        'cie_metrics_summary',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('period_start', sa.DateTime, nullable=False),
        sa.Column('period_end', sa.DateTime, nullable=False),
        sa.Column('count', sa.Integer, nullable=False),
        sa.Column('mean', sa.Float, nullable=False),
        sa.Column('min', sa.Float, nullable=True),
        sa.Column('max', sa.Float, nullable=True),
        sa.Column('p50', sa.Float, nullable=True),
        sa.Column('p95', sa.Float, nullable=True),
        sa.Column('breakdown', JSONB, nullable=True),
        sa.Column('computed_at', sa.DateTime,
                  nullable=False, default=datetime.utcnow),
    )
    op.create_index('idx_cie_metrics_name_period', 'cie_metrics_summary', [
                    'metric_name', 'period_start', 'period_end'])


def downgrade() -> None:
    """Drop CIE core schema tables."""
    op.drop_table('cie_metrics_summary')
    op.drop_table('cie_event_log')
    op.drop_table('cie_harvest_outcomes')
    op.drop_table('cie_actions_user_response')
    op.drop_table('cie_actions_recommended')
    op.drop_table('cie_photos')
    op.drop_table('cie_telemetry_vi')
    op.drop_table('cie_telemetry_weather')
    op.drop_table('cie_soil_baseline')
    op.drop_table('cie_fields')
