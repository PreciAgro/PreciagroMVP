"""Authorization service with RBAC and ABAC support."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db.models import (
    Actor, Role, Permission, RolePermission, ActorRole, ABACPolicy,
    ActorType, HumanRole, TrustLevel
)
from ..db.base import get_db


class AuthorizationService:
    """Service for authorization decisions using RBAC and ABAC."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_permission(
        self,
        actor_id: str,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if actor has permission to perform action on resource.
        
        Uses both RBAC and ABAC:
        1. First checks RBAC (role-based permissions)
        2. Then checks ABAC policies
        3. Returns True only if both allow
        """
        # Get actor
        actor = await self.get_actor_with_roles(actor_id)
        if not actor or not actor.is_active:
            return False
        
        # Check RBAC
        rbac_allowed = await self._check_rbac(actor, resource, action)
        if not rbac_allowed:
            return False
        
        # Check ABAC
        abac_allowed = await self._check_abac(actor, resource, action, context or {})
        if not abac_allowed:
            return False
        
        return True
    
    async def _check_rbac(
        self,
        actor: Actor,
        resource: str,
        action: str,
    ) -> bool:
        """Check RBAC permissions."""
        # Get all active roles for actor
        result = await self.db.execute(
            select(ActorRole).where(
                and_(
                    ActorRole.actor_id == actor.actor_id,
                    ActorRole.revoked_at.is_(None),
                    or_(
                        ActorRole.expires_at.is_(None),
                        ActorRole.expires_at > datetime.now(timezone.utc),
                    ),
                )
            ).options(selectinload(ActorRole.role).selectinload(Role.permissions).selectinload(RolePermission.permission))
        )
        actor_roles = result.scalars().all()
        
        # Check if any role has the required permission
        for actor_role in actor_roles:
            role = actor_role.role
            if not role:
                continue
            
            # Check permissions
            for role_perm in role.permissions:
                perm = role_perm.permission
                if perm.resource == resource and perm.action == action:
                    return True
        
        return False
    
    async def _check_abac(
        self,
        actor: Actor,
        resource: str,
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        """Check ABAC policies."""
        # Get all active ABAC policies
        result = await self.db.execute(
            select(ABACPolicy).where(
                ABACPolicy.is_active == True
            ).order_by(ABACPolicy.priority.desc())
        )
        policies = result.scalars().all()
        
        # Build subject attributes
        subject_attrs = {
            "actor_id": actor.actor_id,
            "actor_type": actor.actor_type.value,
            "trust_level": actor.trust_level.value,
            "region": actor.region,
        }
        
        if actor.actor_type == ActorType.HUMAN and actor.role:
            subject_attrs["role"] = actor.role.value
        
        # Add context attributes
        subject_attrs.update(context.get("subject", {}))
        
        # Build resource attributes
        resource_attrs = {
            "type": resource,
            **context.get("resource", {}),
        }
        
        # Evaluate policies
        for policy in policies:
            policy_def = policy.policy_definition
            
            # Check if policy matches
            if self._evaluate_policy(policy_def, subject_attrs, resource_attrs, action, context):
                # Policy matched - check effect (allow/deny)
                effect = policy_def.get("effect", "allow")
                if effect == "deny":
                    return False  # Explicit deny
                elif effect == "allow":
                    # Check conditions
                    conditions = policy_def.get("conditions", {})
                    if self._evaluate_conditions(conditions, subject_attrs, resource_attrs, context):
                        return True
        
        # Default deny if no policy matches
        return False
    
    def _evaluate_policy(
        self,
        policy_def: Dict[str, Any],
        subject_attrs: Dict[str, Any],
        resource_attrs: Dict[str, Any],
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate if a policy matches the request."""
        # Check subject match
        subject_match = policy_def.get("subject", {})
        if subject_match:
            if not self._match_attributes(subject_match, subject_attrs):
                return False
        
        # Check resource match
        resource_match = policy_def.get("resource", {})
        if resource_match:
            if not self._match_attributes(resource_match, resource_attrs):
                return False
        
        # Check action match
        policy_action = policy_def.get("action")
        if policy_action:
            if isinstance(policy_action, list):
                if action not in policy_action:
                    return False
            elif policy_action != action:
                return False
        
        return True
    
    def _match_attributes(self, pattern: Dict[str, Any], attributes: Dict[str, Any]) -> bool:
        """Match attributes against a pattern."""
        for key, value in pattern.items():
            attr_value = attributes.get(key)
            
            if isinstance(value, list):
                # Check if attribute value is in list
                if attr_value not in value:
                    return False
            elif isinstance(value, dict):
                # Nested matching (e.g., {"$in": [...]})
                if "$in" in value:
                    if attr_value not in value["$in"]:
                        return False
                elif "$not_in" in value:
                    if attr_value in value["$not_in"]:
                        return False
                elif "$exists" in value:
                    exists = key in attributes
                    if exists != value["$exists"]:
                        return False
                else:
                    # Recursive match
                    if not isinstance(attr_value, dict) or not self._match_attributes(value, attr_value):
                        return False
            else:
                # Exact match
                if attr_value != value:
                    return False
        
        return True
    
    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        subject_attrs: Dict[str, Any],
        resource_attrs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate policy conditions."""
        # Time-based conditions
        if "time" in conditions:
            time_cond = conditions["time"]
            now = datetime.now(timezone.utc)
            
            if "before" in time_cond:
                before = datetime.fromisoformat(time_cond["before"].replace("Z", "+00:00"))
                if now >= before:
                    return False
            
            if "after" in time_cond:
                after = datetime.fromisoformat(time_cond["after"].replace("Z", "+00:00"))
                if now < after:
                    return False
        
        # Region-based conditions
        if "region" in conditions:
            allowed_regions = conditions["region"].get("$in", [])
            if allowed_regions and subject_attrs.get("region") not in allowed_regions:
                return False
        
        # Trust level conditions
        if "trust_level" in conditions:
            min_trust = conditions["trust_level"].get("$gte")
            if min_trust:
                trust_levels = ["unverified", "verified", "trusted", "high_trust"]
                actor_trust = subject_attrs.get("trust_level", "unverified")
                if trust_levels.index(actor_trust) < trust_levels.index(min_trust):
                    return False
        
        # Online/offline conditions
        if "online" in conditions:
            is_online = context.get("online", True)
            if conditions["online"] != is_online:
                return False
        
        # Custom conditions (can be extended)
        if "custom" in conditions:
            # Evaluate custom conditions using context
            custom_cond = conditions["custom"]
            # This is a placeholder - implement based on your needs
            pass
        
        return True
    
    async def get_actor_with_roles(self, actor_id: str) -> Optional[Actor]:
        """Get actor with roles loaded."""
        result = await self.db.execute(
            select(Actor).where(Actor.actor_id == actor_id)
            .options(selectinload(Actor.roles_assigned).selectinload(ActorRole.role))
        )
        return result.scalar_one_or_none()
    
    async def assign_role(self, actor_id: str, role_id: str, assigned_by: Optional[str] = None) -> bool:
        """Assign a role to an actor."""
        # Check if already assigned
        result = await self.db.execute(
            select(ActorRole).where(
                and_(
                    ActorRole.actor_id == actor_id,
                    ActorRole.role_id == role_id,
                    ActorRole.revoked_at.is_(None),
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return True  # Already assigned
        
        # Create new assignment
        actor_role = ActorRole(
            actor_id=actor_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        self.db.add(actor_role)
        await self.db.flush()
        return True
    
    async def revoke_role(self, actor_id: str, role_id: str) -> bool:
        """Revoke a role from an actor."""
        result = await self.db.execute(
            select(ActorRole).where(
                and_(
                    ActorRole.actor_id == actor_id,
                    ActorRole.role_id == role_id,
                    ActorRole.revoked_at.is_(None),
                )
            )
        )
        actor_role = result.scalar_one_or_none()
        if actor_role:
            actor_role.revoked_at = datetime.now(timezone.utc)
            await self.db.flush()
            return True
        return False
    
    async def create_role(
        self,
        role_id: str,
        role_name: str,
        description: Optional[str] = None,
        is_system: bool = False,
    ) -> Role:
        """Create a new role."""
        role = Role(
            role_id=role_id,
            role_name=role_name,
            description=description,
            is_system=is_system,
        )
        self.db.add(role)
        await self.db.flush()
        return role
    
    async def create_permission(
        self,
        permission_id: str,
        permission_name: str,
        resource: str,
        action: str,
        description: Optional[str] = None,
    ) -> Permission:
        """Create a new permission."""
        permission = Permission(
            permission_id=permission_id,
            permission_name=permission_name,
            resource=resource,
            action=action,
            description=description,
        )
        self.db.add(permission)
        await self.db.flush()
        return permission
    
    async def assign_permission_to_role(self, role_id: str, permission_id: str) -> bool:
        """Assign a permission to a role."""
        # Check if already assigned
        result = await self.db.execute(
            select(RolePermission).where(
                and_(
                    RolePermission.role_id == role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return True
        
        role_perm = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
        )
        self.db.add(role_perm)
        await self.db.flush()
        return True
    
    async def create_abac_policy(
        self,
        policy_name: str,
        policy_definition: Dict[str, Any],
        description: Optional[str] = None,
        priority: int = 100,
        created_by: Optional[str] = None,
    ) -> ABACPolicy:
        """Create an ABAC policy."""
        policy = ABACPolicy(
            policy_name=policy_name,
            policy_definition=policy_definition,
            description=description,
            priority=priority,
            created_by=created_by,
        )
        self.db.add(policy)
        await self.db.flush()
        return policy

