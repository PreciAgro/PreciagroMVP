"""Database models for Security & Access Engine."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
    UniqueConstraint,
    CheckConstraint,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


# Use JSONB on PostgreSQL, JSON elsewhere
try:
    from sqlalchemy.dialects.postgresql import JSONB

    JSONType = JSONB
except ImportError:
    JSONType = JSON


class ActorType(str, Enum):
    """Types of actors in the system."""

    HUMAN = "human"
    DEVICE = "device"
    SERVICE = "service"
    EXTERNAL = "external"


class HumanRole(str, Enum):
    """Human actor roles."""

    FARMER = "farmer"
    AGRONOMIST = "agronomist"
    ADMIN = "admin"
    SUPPORT = "support"


class TrustLevel(str, Enum):
    """Trust levels for actors."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    HIGH_TRUST = "high_trust"


class TokenType(str, Enum):
    """Types of authentication tokens."""

    ACCESS = "access"
    REFRESH = "refresh"
    SERVICE = "service"
    DEVICE = "device"


class AuditEventType(str, Enum):
    """Types of audit events."""

    AUTH_LOGIN = "auth.login"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_ISSUED = "auth.token_issued"
    AUTH_TOKEN_REVOKED = "auth.token_revoked"
    AUTH_MFA_ENABLED = "auth.mfa_enabled"
    AUTH_MFA_DISABLED = "auth.mfa_disabled"
    PERMISSION_DENIED = "permission.denied"
    PERMISSION_GRANTED = "permission.granted"
    DATA_ACCESS = "data.access"
    DATA_MODIFY = "data.modify"
    DATA_DELETE = "data.delete"
    AI_RECOMMENDATION = "ai.recommendation"
    AI_SAFETY_GATE = "ai.safety_gate"
    ADMIN_ACTION = "admin.action"
    OFFLINE_SYNC = "offline.sync"
    KEY_ROTATION = "key.rotation"
    ENCRYPTION = "encryption.encrypt"
    DECRYPTION = "encryption.decrypt"


class Actor(Base):
    """Actor identity model - supports Human, Device, Service, External."""

    __tablename__ = "security_actors"

    actor_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, default=lambda: f"actor_{uuid4().hex[:16]}"
    )
    actor_type: Mapped[ActorType] = mapped_column(String(20), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Human-specific fields
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    phone: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[Optional[HumanRole]] = mapped_column(String(20), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Device-specific fields
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    device_certificate_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Service-specific fields
    service_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    service_endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Common fields
    trust_level: Mapped[TrustLevel] = mapped_column(
        String(20), default=TrustLevel.UNVERIFIED, nullable=False
    )
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    capabilities: Mapped[dict] = mapped_column(
        JSONType, default=dict, nullable=False
    )  # JSON capabilities
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONType, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Expiry & revocation
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    revocation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tokens: Mapped[list["Token"]] = relationship(
        back_populates="actor", cascade="all, delete-orphan"
    )
    roles_assigned: Mapped[list["ActorRole"]] = relationship(
        back_populates="actor", cascade="all, delete-orphan"
    )
    mfa_devices: Mapped[list["MFADevice"]] = relationship(
        back_populates="actor", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor")

    __table_args__ = (
        Index("idx_actor_type_active", "actor_type", "is_active"),
        Index("idx_actor_region", "region", "is_active"),
        CheckConstraint(
            "actor_type = 'human' OR (email IS NULL AND phone IS NULL)", name="check_human_fields"
        ),
        CheckConstraint("actor_type = 'device' OR device_name IS NULL", name="check_device_fields"),
        CheckConstraint(
            "actor_type = 'service' OR service_name IS NULL", name="check_service_fields"
        ),
    )


class Role(Base):
    """RBAC role definition."""

    __tablename__ = "security_roles"

    role_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    role_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # System roles cannot be deleted

    # Relationships
    permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    actors: Mapped[list["ActorRole"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class Permission(Base):
    """Permission definition for RBAC."""

    __tablename__ = "security_permissions"

    permission_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    permission_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    resource: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g., "farm", "inventory", "recommendation"
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., "read", "write", "delete"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    roles: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
        Index("idx_permission_resource_action", "resource", "action"),
    )


class RolePermission(Base):
    """Many-to-many relationship between roles and permissions."""

    __tablename__ = "security_role_permissions"

    role_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("security_roles.role_id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("security_permissions.permission_id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    role: Mapped["Role"] = relationship(back_populates="permissions")
    permission: Mapped["Permission"] = relationship(back_populates="roles")


class ActorRole(Base):
    """Many-to-many relationship between actors and roles."""

    __tablename__ = "security_actor_roles"

    actor_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("security_actors.actor_id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("security_roles.role_id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assigned_by: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Actor ID who assigned
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    actor: Mapped["Actor"] = relationship(back_populates="roles_assigned")
    role: Mapped["Role"] = relationship(back_populates="actors")

    __table_args__ = (Index("idx_actor_role_active", "actor_id", "role_id", "revoked_at"),)


class Token(Base):
    """Authentication tokens (access, refresh, service, device)."""

    __tablename__ = "security_tokens"

    token_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, default=lambda: f"token_{uuid4().hex[:16]}"
    )
    actor_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("security_actors.actor_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_type: Mapped[TokenType] = mapped_column(String(20), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )  # Hashed token value
    jti: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )  # JWT ID
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    revoked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Token metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    scopes: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )  # List of scopes

    # Refresh token rotation
    parent_token_id: Mapped[Optional[str]] = mapped_column(
        String(100), ForeignKey("security_tokens.token_id", ondelete="SET NULL"), nullable=True
    )
    rotated_from_token_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Previous token ID after rotation

    # Relationships
    actor: Mapped["Actor"] = relationship(back_populates="tokens")

    __table_args__ = (
        Index("idx_token_actor_type", "actor_id", "token_type", "expires_at", "revoked_at"),
        Index("idx_token_active", "expires_at", "revoked_at"),
    )


class MFADevice(Base):
    """Multi-factor authentication devices."""

    __tablename__ = "security_mfa_devices"

    device_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, default=lambda: f"mfa_{uuid4().hex[:16]}"
    )
    actor_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("security_actors.actor_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_type: Mapped[str] = mapped_column(String(20), nullable=False)  # totp, sms, email
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)  # Encrypted secret
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    actor: Mapped["Actor"] = relationship(back_populates="mfa_devices")

    __table_args__ = (Index("idx_mfa_actor_active", "actor_id", "is_active"),)


class EncryptionKey(Base):
    """Encryption keys for envelope encryption."""

    __tablename__ = "security_encryption_keys"

    key_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    key_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # data_encryption, token_signing, etc.
    encrypted_key: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )  # Key encrypted with master key
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="AES-256-GCM")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONType, nullable=True)

    __table_args__ = (
        UniqueConstraint("key_id", "key_version", name="uq_key_id_version"),
        Index("idx_key_type_active", "key_type", "is_active", "expires_at"),
    )


class AuditLog(Base):
    """Immutable audit log for all security-relevant events."""

    __tablename__ = "security_audit_logs"

    log_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, default=lambda: f"audit_{uuid4().hex[:16]}"
    )
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        ForeignKey("security_actors.actor_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[AuditEventType] = mapped_column(String(50), nullable=False, index=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Event details
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )  # e.g., "farm", "inventory"
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    action: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # e.g., "read", "write"

    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional metadata (structured)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONType, nullable=True)

    # Tamper-evident hash (optional, for extra security)
    event_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Relationships
    actor: Mapped[Optional["Actor"]] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_actor_time", "actor_id", "event_timestamp"),
        Index("idx_audit_type_time", "event_type", "event_timestamp"),
        Index("idx_audit_resource", "resource_type", "resource_id", "event_timestamp"),
        Index("idx_audit_region_time", "region", "event_timestamp"),
    )


class ABACPolicy(Base):
    """Attribute-Based Access Control policies."""

    __tablename__ = "security_abac_policies"

    policy_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, default=lambda: f"policy_{uuid4().hex[:16]}"
    )
    policy_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Policy definition (JSON structure)
    # Example: {"subject": {"role": "farmer", "region": "EU"}, "resource": {"type": "farm"}, "action": "read", "conditions": {...}}
    policy_definition: Mapped[dict] = mapped_column(JSONType, nullable=False)

    # Priority (higher = evaluated first)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False, index=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (Index("idx_policy_active_priority", "is_active", "priority"),)
