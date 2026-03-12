"""Farm Inventory Engine - Initial Schema

Revision ID: farm_inventory_v1_0
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'farm_inventory_v1_0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types (PostgreSQL only)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE inventory_category AS ENUM ('seed', 'fertilizer', 'chemical', 'feed', 'tool');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE inventory_unit AS ENUM ('kg', 'liters', 'units', 'tons', 'bags');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE usage_reason AS ENUM ('recommendation', 'manual', 'emergency', 'scheduled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create inventory items table
    op.create_table(
        'farm_inventory_items',
        sa.Column('item_id', sa.String(length=100), nullable=False),
        sa.Column('farmer_id', sa.String(length=100), nullable=False),
        sa.Column('category', sa.Enum('seed', 'fertilizer', 'chemical', 'feed', 'tool', name='inventory_category'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('crop_or_animal', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.Enum('kg', 'liters', 'units', 'tons', 'bags', name='inventory_unit'), nullable=False),
        sa.Column('batch_id', sa.String(length=100), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('cost_per_unit', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('storage_condition', sa.String(length=200), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('item_id')
    )
    
    # Create indexes for inventory items
    op.create_index('idx_farmer_category', 'farm_inventory_items', ['farmer_id', 'category'])
    op.create_index('idx_expiry_date', 'farm_inventory_items', ['expiry_date'])
    op.create_index('idx_last_updated', 'farm_inventory_items', ['last_updated'])
    op.create_index(op.f('ix_farm_inventory_items_farmer_id'), 'farm_inventory_items', ['farmer_id'], unique=False)
    
    # Create usage logs table
    op.create_table(
        'farm_inventory_usage_logs',
        sa.Column('usage_id', sa.String(length=100), nullable=False),
        sa.Column('item_id', sa.String(length=100), nullable=False),
        sa.Column('farmer_id', sa.String(length=100), nullable=False),
        sa.Column('field_id', sa.String(length=100), nullable=True),
        sa.Column('crop_stage', sa.String(length=50), nullable=True),
        sa.Column('quantity_used', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('usage_reason', sa.Enum('recommendation', 'manual', 'emergency', 'scheduled', name='usage_reason'), nullable=False),
        sa.Column('source_engine', sa.String(length=50), nullable=True, comment='Engine that triggered this usage: crop_intelligence, temporal_logic, manual, emergency'),
        sa.Column('action_id', sa.String(length=100), nullable=True, comment='ID of the action/recommendation/task that caused this usage'),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['farm_inventory_items.item_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('usage_id')
    )
    
    # Create indexes for usage logs
    op.create_index('idx_item_timestamp', 'farm_inventory_usage_logs', ['item_id', 'timestamp'])
    op.create_index('idx_farmer_timestamp', 'farm_inventory_usage_logs', ['farmer_id', 'timestamp'])
    op.create_index('idx_field_timestamp', 'farm_inventory_usage_logs', ['field_id', 'timestamp'])
    op.create_index('idx_source_engine', 'farm_inventory_usage_logs', ['source_engine', 'timestamp'])
    op.create_index('idx_action_id', 'farm_inventory_usage_logs', ['action_id'])
    op.create_index(op.f('ix_farm_inventory_usage_logs_item_id'), 'farm_inventory_usage_logs', ['item_id'], unique=False)
    op.create_index(op.f('ix_farm_inventory_usage_logs_farmer_id'), 'farm_inventory_usage_logs', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_farm_inventory_usage_logs_field_id'), 'farm_inventory_usage_logs', ['field_id'], unique=False)
    op.create_index(op.f('ix_farm_inventory_usage_logs_timestamp'), 'farm_inventory_usage_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_farm_inventory_usage_logs_source_engine'), 'farm_inventory_usage_logs', ['source_engine'], unique=False)
    
    # Create alerts table
    op.create_table(
        'farm_inventory_alerts',
        sa.Column('alert_id', sa.String(length=100), nullable=False),
        sa.Column('farmer_id', sa.String(length=100), nullable=False),
        sa.Column('item_id', sa.String(length=100), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['farm_inventory_items.item_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('alert_id')
    )
    
    # Create indexes for alerts
    op.create_index('idx_farmer_resolved', 'farm_inventory_alerts', ['farmer_id', 'resolved'])
    op.create_index('idx_alert_type', 'farm_inventory_alerts', ['alert_type', 'severity'])
    op.create_index(op.f('ix_farm_inventory_alerts_farmer_id'), 'farm_inventory_alerts', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_farm_inventory_alerts_item_id'), 'farm_inventory_alerts', ['item_id'], unique=False)
    op.create_index(op.f('ix_farm_inventory_alerts_created_at'), 'farm_inventory_alerts', ['created_at'], unique=False)
    
    # Create inventory snapshots table
    op.create_table(
        'farm_inventory_snapshots',
        sa.Column('snapshot_id', sa.String(length=100), nullable=False),
        sa.Column('farmer_id', sa.String(length=100), nullable=False),
        sa.Column('snapshot_type', sa.String(length=50), nullable=False),
        sa.Column('triggered_by', sa.String(length=100), nullable=True),
        sa.Column('snapshot_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('snapshot_id')
    )
    
    # Create indexes for snapshots
    op.create_index('idx_farmer_snapshot_type', 'farm_inventory_snapshots', ['farmer_id', 'snapshot_type'])
    op.create_index('idx_created_at', 'farm_inventory_snapshots', ['created_at'])
    op.create_index(op.f('ix_farm_inventory_snapshots_farmer_id'), 'farm_inventory_snapshots', ['farmer_id'], unique=False)
    
    # Create sync state table (for offline-first)
    op.create_table(
        'farm_inventory_sync_state',
        sa.Column('sync_id', sa.String(length=100), nullable=False),
        sa.Column('farmer_id', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('operation', sa.String(length=20), nullable=False),
        sa.Column('local_timestamp', sa.DateTime(), nullable=False),
        sa.Column('synced', sa.Boolean(), nullable=False),
        sa.Column('synced_at', sa.DateTime(), nullable=True),
        sa.Column('conflict_resolved', sa.Boolean(), nullable=False),
        sa.Column('conflict_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('sync_id')
    )
    
    # Create indexes for sync state
    op.create_index('idx_farmer_synced', 'farm_inventory_sync_state', ['farmer_id', 'synced'])
    op.create_index('idx_entity', 'farm_inventory_sync_state', ['entity_type', 'entity_id'])
    op.create_index(op.f('ix_farm_inventory_sync_state_farmer_id'), 'farm_inventory_sync_state', ['farmer_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('farm_inventory_sync_state')
    op.drop_table('farm_inventory_snapshots')
    op.drop_table('farm_inventory_alerts')
    op.drop_table('farm_inventory_usage_logs')
    op.drop_table('farm_inventory_items')
    
    # Drop enum types (PostgreSQL only)
    op.execute('DROP TYPE IF EXISTS usage_reason')
    op.execute('DROP TYPE IF EXISTS inventory_unit')
    op.execute('DROP TYPE IF EXISTS inventory_category')

