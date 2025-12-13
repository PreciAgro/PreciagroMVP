"""
Alembic migration: Security & Access Engine v1.0 - Initial schema
Revision ID: security_access_v1_0
Revises: farm_inventory_v1_0_initial_schema
Create Date: 2025-01-XX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'security_access_v1_0'
down_revision = 'farm_inventory_v1_0_initial_schema'  # Adjust based on your latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Security & Access Engine schema."""
    
    # ============================================
    # 1. Actors Table
    # ============================================
    op.create_table(
        'security_actors',
        sa.Column('actor_id', sa.String(100), primary_key=True),
        sa.Column('actor_type', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        
        # Human-specific
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('role', sa.String(20), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        
        # Device-specific
        sa.Column('device_name', sa.String(255), nullable=True),
        sa.Column('device_fingerprint', sa.String(255), nullable=True),
        sa.Column('device_certificate_id', sa.String(100), nullable=True),
        
        # Service-specific
        sa.Column('service_name', sa.String(100), nullable=True),
        sa.Column('service_endpoint', sa.String(500), nullable=True),
        
        # Common
        sa.Column('trust_level', sa.String(20), nullable=False, server_default='unverified'),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('capabilities', JSONB, nullable=False, server_default='{}'),
        sa.Column('metadata', JSONB, nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        
        # Expiry & revocation
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revocation_reason', sa.Text, nullable=True),
    )
    op.create_index('idx_actor_type', 'security_actors', ['actor_type'])
    op.create_index('idx_actor_email', 'security_actors', ['email'], unique=True, postgresql_where=sa.text('email IS NOT NULL'))
    op.create_index('idx_actor_phone', 'security_actors', ['phone'], unique=True, postgresql_where=sa.text('phone IS NOT NULL'))
    op.create_index('idx_actor_service_name', 'security_actors', ['service_name'], unique=True, postgresql_where=sa.text('service_name IS NOT NULL'))
    op.create_index('idx_actor_device_fingerprint', 'security_actors', ['device_fingerprint'])
    op.create_index('idx_actor_type_active', 'security_actors', ['actor_type', 'is_active'])
    op.create_index('idx_actor_region', 'security_actors', ['region', 'is_active'])
    
    # ============================================
    # 2. Roles Table
    # ============================================
    op.create_table(
        'security_roles',
        sa.Column('role_id', sa.String(100), primary_key=True),
        sa.Column('role_name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_system', sa.Boolean, nullable=False, server_default='false'),
    )
    op.create_index('idx_role_name', 'security_roles', ['role_name'])
    
    # ============================================
    # 3. Permissions Table
    # ============================================
    op.create_table(
        'security_permissions',
        sa.Column('permission_id', sa.String(100), primary_key=True),
        sa.Column('permission_name', sa.String(100), unique=True, nullable=False),
        sa.Column('resource', sa.String(100), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_permission_name', 'security_permissions', ['permission_name'])
    op.create_index('idx_permission_resource', 'security_permissions', ['resource'])
    op.create_index('idx_permission_action', 'security_permissions', ['action'])
    op.create_index('idx_permission_resource_action', 'security_permissions', ['resource', 'action'])
    op.create_unique_constraint('uq_permission_resource_action', 'security_permissions', ['resource', 'action'])
    
    # ============================================
    # 4. Role Permissions (Many-to-Many)
    # ============================================
    op.create_table(
        'security_role_permissions',
        sa.Column('role_id', sa.String(100), sa.ForeignKey('security_roles.role_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('permission_id', sa.String(100), sa.ForeignKey('security_permissions.permission_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # ============================================
    # 5. Actor Roles (Many-to-Many)
    # ============================================
    op.create_table(
        'security_actor_roles',
        sa.Column('actor_id', sa.String(100), sa.ForeignKey('security_actors.actor_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', sa.String(100), sa.ForeignKey('security_roles.role_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('assigned_by', sa.String(100), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_actor_role_active', 'security_actor_roles', ['actor_id', 'role_id', 'revoked_at'])
    
    # ============================================
    # 6. Tokens Table
    # ============================================
    op.create_table(
        'security_tokens',
        sa.Column('token_id', sa.String(100), primary_key=True),
        sa.Column('actor_id', sa.String(100), sa.ForeignKey('security_actors.actor_id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_type', sa.String(20), nullable=False),
        sa.Column('token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('jti', sa.String(100), unique=True, nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.Text, nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('device_id', sa.String(100), nullable=True),
        sa.Column('scopes', JSONB, nullable=False, server_default='[]'),
        sa.Column('parent_token_id', sa.String(100), sa.ForeignKey('security_tokens.token_id', ondelete='SET NULL'), nullable=True),
        sa.Column('rotated_from_token_id', sa.String(100), nullable=True),
    )
    op.create_index('idx_token_actor', 'security_tokens', ['actor_id'])
    op.create_index('idx_token_type', 'security_tokens', ['token_type'])
    op.create_index('idx_token_hash', 'security_tokens', ['token_hash'], unique=True)
    op.create_index('idx_token_jti', 'security_tokens', ['jti'], unique=True, postgresql_where=sa.text('jti IS NOT NULL'))
    op.create_index('idx_token_actor_type', 'security_tokens', ['actor_id', 'token_type', 'expires_at', 'revoked_at'])
    op.create_index('idx_token_active', 'security_tokens', ['expires_at', 'revoked_at'])
    op.create_index('idx_token_device', 'security_tokens', ['device_id'])
    
    # ============================================
    # 7. MFA Devices Table
    # ============================================
    op.create_table(
        'security_mfa_devices',
        sa.Column('device_id', sa.String(100), primary_key=True),
        sa.Column('actor_id', sa.String(100), sa.ForeignKey('security_actors.actor_id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_type', sa.String(20), nullable=False),
        sa.Column('device_name', sa.String(255), nullable=True),
        sa.Column('secret', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_mfa_actor', 'security_mfa_devices', ['actor_id'])
    op.create_index('idx_mfa_actor_active', 'security_mfa_devices', ['actor_id', 'is_active'])
    
    # ============================================
    # 8. Encryption Keys Table
    # ============================================
    op.create_table(
        'security_encryption_keys',
        sa.Column('key_id', sa.String(100), primary_key=True),
        sa.Column('key_version', sa.Integer, nullable=False),
        sa.Column('key_type', sa.String(50), nullable=False),
        sa.Column('encrypted_key', sa.LargeBinary, nullable=False),
        sa.Column('algorithm', sa.String(50), nullable=False, server_default='AES-256-GCM'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('metadata', JSONB, nullable=True),
    )
    op.create_index('idx_key_id_version', 'security_encryption_keys', ['key_id', 'key_version'])
    op.create_unique_constraint('uq_key_id_version', 'security_encryption_keys', ['key_id', 'key_version'])
    op.create_index('idx_key_type_active', 'security_encryption_keys', ['key_type', 'is_active', 'expires_at'])
    
    # ============================================
    # 9. Audit Logs Table
    # ============================================
    op.create_table(
        'security_audit_logs',
        sa.Column('log_id', sa.String(100), primary_key=True),
        sa.Column('actor_id', sa.String(100), sa.ForeignKey('security_actors.actor_id', ondelete='SET NULL'), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('event_hash', sa.String(255), nullable=True),
    )
    op.create_index('idx_audit_actor', 'security_audit_logs', ['actor_id'])
    op.create_index('idx_audit_event_type', 'security_audit_logs', ['event_type'])
    op.create_index('idx_audit_timestamp', 'security_audit_logs', ['event_timestamp'])
    op.create_index('idx_audit_actor_time', 'security_audit_logs', ['actor_id', 'event_timestamp'])
    op.create_index('idx_audit_type_time', 'security_audit_logs', ['event_type', 'event_timestamp'])
    op.create_index('idx_audit_resource', 'security_audit_logs', ['resource_type', 'resource_id', 'event_timestamp'])
    op.create_index('idx_audit_region_time', 'security_audit_logs', ['region', 'event_timestamp'])
    op.create_index('idx_audit_success', 'security_audit_logs', ['success'])
    op.create_index('idx_audit_hash', 'security_audit_logs', ['event_hash'], postgresql_where=sa.text('event_hash IS NOT NULL'))
    
    # ============================================
    # 10. ABAC Policies Table
    # ============================================
    op.create_table(
        'security_abac_policies',
        sa.Column('policy_id', sa.String(100), primary_key=True),
        sa.Column('policy_name', sa.String(255), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('policy_definition', JSONB, nullable=False),
        sa.Column('priority', sa.Integer, nullable=False, server_default='100'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=True),
    )
    op.create_index('idx_policy_name', 'security_abac_policies', ['policy_name'], unique=True)
    op.create_index('idx_policy_active_priority', 'security_abac_policies', ['is_active', 'priority'])


def downgrade() -> None:
    """Drop Security & Access Engine schema."""
    op.drop_table('security_abac_policies')
    op.drop_table('security_audit_logs')
    op.drop_table('security_encryption_keys')
    op.drop_table('security_mfa_devices')
    op.drop_table('security_tokens')
    op.drop_table('security_actor_roles')
    op.drop_table('security_role_permissions')
    op.drop_table('security_permissions')
    op.drop_table('security_roles')
    op.drop_table('security_actors')

