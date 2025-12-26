"""initial_normalized_items_and_cursors

Revision ID: 0001_initial
Revises: 
Create Date: 2025-08-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'normalized_items',
        sa.Column('item_id', sa.String(length=36), primary_key=True),
        sa.Column('source_id', sa.String(length=200), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('kind', sa.String(length=100), nullable=False),
        sa.Column('location', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('raw_ref', sa.String(length=500), nullable=True),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
    )
    op.create_unique_constraint('uq_normalized_source_content', 'normalized_items', [
                                'source_id', 'content_hash'])

    op.create_table(
        'sync_cursors',
        sa.Column('source_id', sa.String(length=200), primary_key=True),
        sa.Column('last_observed_at', sa.DateTime(
            timezone=True), nullable=True),
        sa.Column('last_content_hash', sa.String(length=128), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text('now()')),
    )


def downgrade():
    op.drop_table('sync_cursors')
    op.drop_constraint('uq_normalized_source_content',
                       'normalized_items', type_='unique')
    op.drop_table('normalized_items')
