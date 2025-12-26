"""Identity service for managing actors."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Actor, ActorType, HumanRole, TrustLevel
from ..core.config import settings


class IdentityService:
    """Service for managing actor identities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_actor(
        self,
        actor_type: ActorType,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        password_hash: Optional[str] = None,
        role: Optional[HumanRole] = None,
        full_name: Optional[str] = None,
        device_name: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        service_name: Optional[str] = None,
        service_endpoint: Optional[str] = None,
        region: Optional[str] = None,
        capabilities: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Actor:
        """Create a new actor."""
        actor_id = f"actor_{uuid4().hex[:16]}"

        actor = Actor(
            actor_id=actor_id,
            actor_type=actor_type,
            email=email,
            phone=phone,
            password_hash=password_hash,
            role=role,
            full_name=full_name,
            device_name=device_name,
            device_fingerprint=device_fingerprint,
            service_name=service_name,
            service_endpoint=service_endpoint,
            region=region,
            capabilities=capabilities or {},
            metadata_=metadata,
            trust_level=TrustLevel.UNVERIFIED,
        )

        self.db.add(actor)
        await self.db.flush()
        return actor

    async def get_actor_by_id(self, actor_id: str) -> Optional[Actor]:
        """Get actor by ID."""
        result = await self.db.execute(select(Actor).where(Actor.actor_id == actor_id))
        return result.scalar_one_or_none()

    async def get_actor_by_email(self, email: str) -> Optional[Actor]:
        """Get actor by email."""
        result = await self.db.execute(
            select(Actor).where(
                and_(
                    Actor.email == email,
                    Actor.actor_type == ActorType.HUMAN,
                    Actor.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_actor_by_phone(self, phone: str) -> Optional[Actor]:
        """Get actor by phone."""
        result = await self.db.execute(
            select(Actor).where(
                and_(
                    Actor.phone == phone,
                    Actor.actor_type == ActorType.HUMAN,
                    Actor.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_actor_by_device_fingerprint(self, fingerprint: str) -> Optional[Actor]:
        """Get actor by device fingerprint."""
        result = await self.db.execute(
            select(Actor).where(
                and_(
                    Actor.device_fingerprint == fingerprint,
                    Actor.actor_type == ActorType.DEVICE,
                    Actor.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_actor_by_service_name(self, service_name: str) -> Optional[Actor]:
        """Get actor by service name."""
        result = await self.db.execute(
            select(Actor).where(
                and_(
                    Actor.service_name == service_name,
                    Actor.actor_type == ActorType.SERVICE,
                    Actor.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_actor(self, actor_id: str, **updates) -> Optional[Actor]:
        """Update actor fields."""
        actor = await self.get_actor_by_id(actor_id)
        if not actor:
            return None

        for key, value in updates.items():
            if hasattr(actor, key):
                setattr(actor, key, value)

        actor.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return actor

    async def verify_actor(self, actor_id: str) -> bool:
        """Mark actor as verified."""
        actor = await self.get_actor_by_id(actor_id)
        if not actor:
            return False

        actor.is_verified = True
        actor.verified_at = datetime.now(timezone.utc)
        if actor.trust_level == TrustLevel.UNVERIFIED:
            actor.trust_level = TrustLevel.VERIFIED
        await self.db.flush()
        return True

    async def revoke_actor(self, actor_id: str, reason: Optional[str] = None) -> bool:
        """Revoke an actor."""
        actor = await self.get_actor_by_id(actor_id)
        if not actor:
            return False

        actor.is_active = False
        actor.revoked_at = datetime.now(timezone.utc)
        actor.revocation_reason = reason
        await self.db.flush()
        return True

    async def update_last_login(self, actor_id: str) -> None:
        """Update last login timestamp."""
        actor = await self.get_actor_by_id(actor_id)
        if actor:
            actor.last_login_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def set_trust_level(self, actor_id: str, trust_level: TrustLevel) -> bool:
        """Set actor trust level."""
        actor = await self.get_actor_by_id(actor_id)
        if not actor:
            return False

        actor.trust_level = trust_level
        await self.db.flush()
        return True
