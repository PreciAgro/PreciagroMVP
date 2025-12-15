"""Database models for Farm Inventory Engine."""

from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

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


class InventoryCategory(sa.Enum):
    """Inventory item categories."""

    SEED = "seed"
    FERTILIZER = "fertilizer"
    CHEMICAL = "chemical"
    FEED = "feed"
    TOOL = "tool"


class InventoryUnit(sa.Enum):
    """Inventory quantity units."""

    KG = "kg"
    LITERS = "liters"
    UNITS = "units"
    TONS = "tons"
    BAGS = "bags"


class InventoryItem(Base):
    """Inventory item model - tracks farm inputs."""

    __tablename__ = "farm_inventory_items"

    item_id: Mapped[str] = mapped_column(
        sa.String(100), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    farmer_id: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        sa.Enum(InventoryCategory, name="inventory_category"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    crop_or_animal: Mapped[str | None] = mapped_column(sa.String(100))
    quantity: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    unit: Mapped[str] = mapped_column(sa.Enum(InventoryUnit, name="inventory_unit"), nullable=False)
    batch_id: Mapped[str | None] = mapped_column(sa.String(100))
    expiry_date: Mapped[date | None] = mapped_column(sa.Date)
    purchase_date: Mapped[date | None] = mapped_column(sa.Date)
    cost_per_unit: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    storage_condition: Mapped[str | None] = mapped_column(sa.String(200))
    last_updated: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, nullable=False
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)

    # Indexes for common queries
    __table_args__ = (
        sa.Index("idx_farmer_category", "farmer_id", "category"),
        sa.Index("idx_expiry_date", "expiry_date"),
        sa.Index("idx_last_updated", "last_updated"),
    )


class UsageReason(sa.Enum):
    """Reason for inventory usage."""

    RECOMMENDATION = "recommendation"
    MANUAL = "manual"
    EMERGENCY = "emergency"
    SCHEDULED = "scheduled"


class UsageLog(Base):
    """Usage log model - tracks all inventory deductions (never deleted)."""

    __tablename__ = "farm_inventory_usage_logs"

    usage_id: Mapped[str] = mapped_column(
        sa.String(100), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    item_id: Mapped[str] = mapped_column(
        sa.String(100),
        sa.ForeignKey("farm_inventory_items.item_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    farmer_id: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    field_id: Mapped[str | None] = mapped_column(sa.String(100), index=True)
    crop_stage: Mapped[str | None] = mapped_column(sa.String(50))
    quantity_used: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    usage_reason: Mapped[str] = mapped_column(
        sa.Enum(UsageReason, name="usage_reason"), nullable=False
    )
    source_engine: Mapped[str | None] = mapped_column(
        sa.String(50),
        index=True,
        comment="Engine that triggered this usage: crop_intelligence, temporal_logic, manual, emergency",
    )
    action_id: Mapped[str | None] = mapped_column(
        sa.String(100),
        index=True,
        comment="ID of the action/recommendation/task that caused this usage",
    )
    timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)

    # Indexes for common queries
    __table_args__ = (
        sa.Index("idx_item_timestamp", "item_id", "timestamp"),
        sa.Index("idx_farmer_timestamp", "farmer_id", "timestamp"),
        sa.Index("idx_field_timestamp", "field_id", "timestamp"),
        sa.Index("idx_source_engine", "source_engine", "timestamp"),
        sa.Index("idx_action_id", "action_id"),
    )


class InventoryAlert(Base):
    """Alert model - tracks low stock, expiry, and critical shortages."""

    __tablename__ = "farm_inventory_alerts"

    alert_id: Mapped[str] = mapped_column(
        sa.String(100), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    farmer_id: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(
        sa.String(100),
        sa.ForeignKey("farm_inventory_items.item_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False  # "low_stock", "critical", "expiry", "depletion"
    )
    severity: Mapped[str] = mapped_column(sa.String(20), nullable=False)  # "warning", "critical"
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(sa.DateTime)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)

    # Indexes
    __table_args__ = (
        sa.Index("idx_farmer_resolved", "farmer_id", "resolved"),
        sa.Index("idx_alert_type", "alert_type", "severity"),
    )


class InventorySnapshot(Base):
    """Inventory snapshot model - captures inventory state at a point in time.

    Used for:
    - Disputes and audits
    - Explainability ("what was the inventory when this recommendation was made?")
    - Historical analysis
    """

    __tablename__ = "farm_inventory_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        sa.String(100), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    farmer_id: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False  # "daily", "pre_action", "manual"
    )
    triggered_by: Mapped[str | None] = mapped_column(
        sa.String(100),  # "system", "action_id", "user_id"
    )
    snapshot_data: Mapped[dict] = mapped_column(
        JSONType,
        nullable=False,
        comment="JSON array of inventory items with quantities at snapshot time",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType)

    # Indexes
    __table_args__ = (
        sa.Index("idx_farmer_snapshot_type", "farmer_id", "snapshot_type"),
        sa.Index("idx_created_at", "created_at"),
    )


class SyncState(Base):
    """Sync state model - tracks offline-first synchronization."""

    __tablename__ = "farm_inventory_sync_state"

    sync_id: Mapped[str] = mapped_column(
        sa.String(100), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    farmer_id: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )  # "item", "usage", "alert"
    entity_id: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    operation: Mapped[str] = mapped_column(
        sa.String(20), nullable=False
    )  # "create", "update", "delete"
    local_timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow, nullable=False
    )
    synced: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime)
    conflict_resolved: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    conflict_data: Mapped[dict | None] = mapped_column("conflict_data", JSONType)

    # Indexes
    __table_args__ = (
        sa.Index("idx_farmer_synced", "farmer_id", "synced"),
        sa.Index("idx_entity", "entity_type", "entity_id"),
    )
