"""Initial FLE tables

Revision ID: 001_initial
Revises:
Create Date: 2024-12-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create feedback_events table (append-only)
    op.create_table(
        "feedback_events",
        sa.Column("feedback_id", sa.String(36), primary_key=True),
        sa.Column("recommendation_id", sa.String(36), nullable=False, index=True),
        sa.Column("reasoning_trace_id", sa.String(36), nullable=True, index=True),
        sa.Column("decision_id", sa.String(36), nullable=True),
        sa.Column("feedback_type", sa.String(20), nullable=False, index=True),
        sa.Column("source_engine", sa.String(50), nullable=False, index=True),
        sa.Column("region_code", sa.String(10), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("user_role", sa.String(20), nullable=False, default="farmer"),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("feedback_category", sa.String(50), nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("view_duration_seconds", sa.Float, nullable=True),
        sa.Column("clicked_action", sa.Boolean, nullable=True),
        sa.Column("dismissed", sa.Boolean, nullable=True),
        sa.Column("action_executed", sa.Boolean, nullable=True),
        sa.Column("outcome_category", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("received_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("correlation_id", sa.String(36), nullable=False, index=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("is_valid", sa.Boolean, nullable=False, default=True),
        sa.Column("validation_errors", postgresql.JSONB, nullable=False, default=[]),
        sa.Column("metadata", postgresql.JSONB, nullable=False, default={}),
    )

    op.create_index(
        "ix_feedback_events_rec_type", "feedback_events", ["recommendation_id", "feedback_type"]
    )
    op.create_index(
        "ix_feedback_events_region_time", "feedback_events", ["region_code", "created_at"]
    )
    op.create_index("ix_feedback_events_user_time", "feedback_events", ["user_id", "created_at"])

    # Create weighted_feedback table
    op.create_table(
        "weighted_feedback",
        sa.Column("weighted_id", sa.String(36), primary_key=True),
        sa.Column(
            "source_feedback_id",
            sa.String(36),
            sa.ForeignKey("feedback_events.feedback_id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("recommendation_id", sa.String(36), nullable=False, index=True),
        sa.Column("final_weight", sa.Float, nullable=False),
        sa.Column("base_confidence", sa.Float, nullable=False),
        sa.Column("farmer_experience_factor", sa.Float, nullable=False),
        sa.Column("historical_accuracy_factor", sa.Float, nullable=False),
        sa.Column("model_confidence_factor", sa.Float, nullable=False),
        sa.Column("environmental_stability_factor", sa.Float, nullable=False),
        sa.Column("trust_score", sa.Float, nullable=False),
        sa.Column("quality_score", sa.Float, nullable=False),
        sa.Column("is_flagged", sa.Boolean, nullable=False, default=False, index=True),
        sa.Column("flag_reasons", postgresql.JSONB, nullable=False, default=[]),
        sa.Column("is_noise", sa.Boolean, nullable=False, default=False),
        sa.Column("is_duplicate", sa.Boolean, nullable=False, default=False),
        sa.Column("is_contradiction", sa.Boolean, nullable=False, default=False),
        sa.Column("duplicate_of_id", sa.String(36), nullable=True),
        sa.Column("contradiction_with_ids", postgresql.JSONB, nullable=False, default=[]),
        sa.Column("region_code", sa.String(10), nullable=False, index=True),
        sa.Column("weighting_version", sa.String(10), nullable=False, default="1.0"),
        sa.Column("processed_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("audit_trace_id", sa.String(36), nullable=True, index=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, default={}),
    )

    op.create_index(
        "ix_weighted_feedback_rec_weight",
        "weighted_feedback",
        ["recommendation_id", "final_weight"],
    )
    op.create_index(
        "ix_weighted_feedback_region_flagged", "weighted_feedback", ["region_code", "is_flagged"]
    )

    # Create learning_signals table
    op.create_table(
        "learning_signals",
        sa.Column("signal_id", sa.String(36), primary_key=True),
        sa.Column("version", sa.String(10), nullable=False, default="1.0"),
        sa.Column("signal_type", sa.String(30), nullable=False, index=True),
        sa.Column("signal_strength", sa.Float, nullable=False),
        sa.Column("source_feedback_ids", postgresql.JSONB, nullable=False),
        sa.Column("source_weighted_ids", postgresql.JSONB, nullable=False, default=[]),
        sa.Column("recommendation_id", sa.String(36), nullable=False, index=True),
        sa.Column("reasoning_trace_id", sa.String(36), nullable=True),
        sa.Column("target_engine", sa.String(30), nullable=False, index=True),
        sa.Column("region_scope", sa.String(10), nullable=False, index=True),
        sa.Column("cross_region_propagation", sa.Boolean, nullable=False, default=False),
        sa.Column("model_id", sa.String(100), nullable=True, index=True),
        sa.Column("model_version", sa.String(20), nullable=True),
        sa.Column("model_type", sa.String(30), nullable=True),
        sa.Column("feedback_count", sa.Integer, nullable=False),
        sa.Column("average_weight", sa.Float, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("feedback_window_start", sa.DateTime, nullable=False),
        sa.Column("feedback_window_end", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.now(), index=True),
        sa.Column("is_routed", sa.Boolean, nullable=False, default=False, index=True),
        sa.Column("routed_at", sa.DateTime, nullable=True),
        sa.Column("routing_stream", sa.String(100), nullable=True),
        sa.Column("correlation_id", sa.String(36), nullable=False, index=True),
        sa.Column("audit_trace_id", sa.String(36), nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=False, default={}),
        sa.Column("metadata", postgresql.JSONB, nullable=False, default={}),
    )

    op.create_index(
        "ix_learning_signals_target_routed", "learning_signals", ["target_engine", "is_routed"]
    )
    op.create_index(
        "ix_learning_signals_rec_type", "learning_signals", ["recommendation_id", "signal_type"]
    )
    op.create_index(
        "ix_learning_signals_model_strength", "learning_signals", ["model_id", "signal_strength"]
    )

    # Create feedback_audit_traces table
    op.create_table(
        "feedback_audit_traces",
        sa.Column("trace_id", sa.String(36), primary_key=True),
        sa.Column("source_feedback_id", sa.String(36), nullable=False, index=True),
        sa.Column("recommendation_id", sa.String(36), nullable=False, index=True),
        sa.Column("weighted_feedback_id", sa.String(36), nullable=True, index=True),
        sa.Column("learning_signal_ids", postgresql.JSONB, nullable=False, default=[]),
        sa.Column("flag_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="processing", index=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=False, default=sa.func.now(), index=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("total_duration_ms", sa.Integer, nullable=True),
        sa.Column("correlation_id", sa.String(36), nullable=False, index=True),
        sa.Column("signature", sa.Text, nullable=True),
        sa.Column("signature_algorithm", sa.String(20), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, default={}),
    )

    op.create_index(
        "ix_audit_traces_rec_status", "feedback_audit_traces", ["recommendation_id", "status"]
    )

    # Create audit_steps table
    op.create_table(
        "audit_steps",
        sa.Column("step_id", sa.String(36), primary_key=True),
        sa.Column(
            "trace_id",
            sa.String(36),
            sa.ForeignKey("feedback_audit_traces.trace_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("input_artifact_id", sa.String(36), nullable=True),
        sa.Column("input_artifact_type", sa.String(30), nullable=True),
        sa.Column("output_artifact_id", sa.String(36), nullable=True),
        sa.Column("output_artifact_type", sa.String(30), nullable=True),
        sa.Column("transformation_applied", sa.String(100), nullable=True),
        sa.Column("transformation_params", postgresql.JSONB, nullable=False, default={}),
        sa.Column("values_before", postgresql.JSONB, nullable=False, default={}),
        sa.Column("values_after", postgresql.JSONB, nullable=False, default={}),
        sa.Column("success", sa.Boolean, nullable=False, default=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, default={}),
    )

    op.create_index("ix_audit_steps_trace_number", "audit_steps", ["trace_id", "step_number"])


def downgrade() -> None:
    op.drop_table("audit_steps")
    op.drop_table("feedback_audit_traces")
    op.drop_table("learning_signals")
    op.drop_table("weighted_feedback")
    op.drop_table("feedback_events")
