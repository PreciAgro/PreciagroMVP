"""Authentication service for various auth methods."""

import secrets
import pyotp
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Actor, ActorType, MFADevice, TrustLevel, AuditEventType
from .identity_service import IdentityService
from .password_service import PasswordService
from .token_service import TokenService
from .audit_service import AuditService
from ..core.config import settings


class AuthenticationService:
    """Service for authentication (password, OTP, MFA)."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.identity_service = IdentityService(db)
        self.password_service = PasswordService()
        self.token_service = TokenService(db)
        self.audit_service = AuditService(db)

    async def authenticate_with_password(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        password: str = "",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[Actor], Optional[str], Optional[str], bool]:
        """Authenticate with email/phone and password.

        Returns:
            Tuple of (actor, access_token, refresh_token, requires_mfa)
        """
        # Get actor
        if email:
            actor = await self.identity_service.get_actor_by_email(email)
        elif phone:
            actor = await self.identity_service.get_actor_by_phone(phone)
        else:
            await self.audit_service.log_auth_event(
                AuditEventType.AUTH_LOGIN_FAILED,
                None,
                False,
                ip_address,
                user_agent,
                "Missing email or phone",
            )
            return None, None, None, False

        if not actor or not actor.is_active:
            await self.audit_service.log_auth_event(
                AuditEventType.AUTH_LOGIN_FAILED,
                actor.actor_id if actor else None,
                False,
                ip_address,
                user_agent,
                "Actor not found or inactive",
            )
            return None, None, None, False

        # Verify password
        if not actor.password_hash or not self.password_service.verify_password(
            password, actor.password_hash
        ):
            await self.audit_service.log_auth_event(
                AuditEventType.AUTH_LOGIN_FAILED,
                actor.actor_id,
                False,
                ip_address,
                user_agent,
                "Invalid password",
            )
            return None, None, None, False

        # Check if MFA is required
        mfa_devices = [d for d in actor.mfa_devices if d.is_active and d.is_verified]
        requires_mfa = len(mfa_devices) > 0

        if requires_mfa:
            # Return actor but no tokens yet - MFA must be completed
            await self.audit_service.log_auth_event(
                AuditEventType.AUTH_LOGIN,
                actor.actor_id,
                True,
                ip_address,
                user_agent,
                metadata={"mfa_required": True},
            )
            return actor, None, None, True

        # Generate tokens
        access_token, _ = await self.token_service.create_access_token(
            actor.actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        refresh_token, _ = await self.token_service.create_refresh_token(
            actor.actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Update last login
        await self.identity_service.update_last_login(actor.actor_id)

        await self.audit_service.log_auth_event(
            AuditEventType.AUTH_LOGIN,
            actor.actor_id,
            True,
            ip_address,
            user_agent,
        )

        return actor, access_token, refresh_token, False

    async def authenticate_with_otp(
        self,
        phone: str,
        otp_code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[Actor], Optional[str], Optional[str]]:
        """Authenticate with phone and OTP (SMS).

        Note: OTP generation and SMS sending should be handled separately.
        This method verifies the OTP.
        """
        actor = await self.identity_service.get_actor_by_phone(phone)
        if not actor or not actor.is_active:
            await self.audit_service.log_auth_event(
                AuditEventType.AUTH_LOGIN_FAILED,
                None,
                False,
                ip_address,
                user_agent,
                "Actor not found",
            )
            return None, None, None

        # In a real implementation, you'd verify OTP from Redis/cache
        # For now, this is a placeholder
        # TODO: Implement OTP verification

        # Generate tokens
        access_token, _ = await self.token_service.create_access_token(
            actor.actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        refresh_token, _ = await self.token_service.create_refresh_token(
            actor.actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.identity_service.update_last_login(actor.actor_id)

        await self.audit_service.log_auth_event(
            AuditEventType.AUTH_LOGIN,
            actor.actor_id,
            True,
            ip_address,
            user_agent,
            metadata={"method": "otp"},
        )

        return actor, access_token, refresh_token

    async def verify_mfa(
        self,
        actor_id: str,
        mfa_code: str,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], bool]:
        """Verify MFA code and issue tokens.

        Returns:
            Tuple of (access_token, refresh_token, success)
        """
        actor = await self.identity_service.get_actor_by_id(actor_id)
        if not actor:
            return None, None, False

        # Get MFA devices
        mfa_devices = [d for d in actor.mfa_devices if d.is_active and d.is_verified]
        if not mfa_devices:
            return None, None, False

        # Verify code against devices
        verified = False
        for device in mfa_devices:
            if device_id and device.device_id != device_id:
                continue

            if device.device_type == "totp":
                totp = pyotp.TOTP(device.secret)
                if totp.verify(mfa_code, valid_window=settings.TOTP_VALIDITY_WINDOW):
                    verified = True
                    device.last_used_at = datetime.now(timezone.utc)
                    await self.db.flush()
                    break

        if not verified:
            await self.audit_service.log_auth_event(
                AuditEventType.AUTH_LOGIN_FAILED,
                actor_id,
                False,
                ip_address,
                user_agent,
                "Invalid MFA code",
            )
            return None, None, False

        # Generate tokens
        access_token, _ = await self.token_service.create_access_token(
            actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        refresh_token, _ = await self.token_service.create_refresh_token(
            actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.identity_service.update_last_login(actor_id)

        await self.audit_service.log_auth_event(
            AuditEventType.AUTH_LOGIN,
            actor_id,
            True,
            ip_address,
            user_agent,
            metadata={"mfa_verified": True},
        )

        return access_token, refresh_token, True

    async def register_mfa_device(
        self,
        actor_id: str,
        device_type: str = "totp",
        device_name: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Register a new MFA device.

        Returns:
            Tuple of (device_id, secret/provisioning_uri)
        """
        actor = await self.identity_service.get_actor_by_id(actor_id)
        if not actor:
            raise ValueError("Actor not found")

        if device_type == "totp":
            # Generate TOTP secret
            secret = pyotp.random_base32()
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=actor.email or actor.phone or actor.actor_id,
                issuer_name=settings.MFA_ISSUER_NAME,
            )

            # Store device (secret should be encrypted in production)
            device = MFADevice(
                device_id=f"mfa_{secrets.token_hex(8)}",
                actor_id=actor_id,
                device_type="totp",
                device_name=device_name or "TOTP Device",
                secret=secret,  # TODO: Encrypt this
                is_active=True,
                is_verified=False,  # Must verify before use
            )
            self.db.add(device)
            await self.db.flush()

            await self.audit_service.log_auth_event(
                AuditEventType.AUTH_MFA_ENABLED,
                actor_id,
                True,
                metadata={"device_type": device_type, "device_id": device.device_id},
            )

            return device.device_id, provisioning_uri
        else:
            raise ValueError(f"Unsupported MFA device type: {device_type}")

    async def verify_mfa_device(
        self,
        actor_id: str,
        device_id: str,
        verification_code: str,
    ) -> bool:
        """Verify an MFA device with a code."""
        actor = await self.identity_service.get_actor_by_id(actor_id)
        if not actor:
            return False

        # Find device
        device = next((d for d in actor.mfa_devices if d.device_id == device_id), None)
        if not device:
            return False

        # Verify code
        if device.device_type == "totp":
            totp = pyotp.TOTP(device.secret)
            if totp.verify(verification_code, valid_window=settings.TOTP_VALIDITY_WINDOW):
                device.is_verified = True
                await self.db.flush()
                return True

        return False

    async def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], bool]:
        """Refresh access token using refresh token.

        Returns:
            Tuple of (new_access_token, new_refresh_token, success)
        """
        # Verify refresh token
        payload = await self.token_service.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None, None, False

        actor_id = payload.get("sub")
        if not actor_id:
            return None, None, False

        # Rotate refresh token
        new_refresh_token, _ = await self.token_service.rotate_refresh_token(
            refresh_token,
            actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Create new access token
        new_access_token, _ = await self.token_service.create_access_token(
            actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return new_access_token, new_refresh_token, True

    async def logout(
        self,
        access_token: str,
        revoke_all: bool = False,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Logout and revoke tokens."""
        payload = await self.token_service.verify_token(access_token)
        if not payload:
            return False

        actor_id = payload.get("sub")
        if not actor_id:
            return False

        if revoke_all:
            await self.token_service.revoke_all_tokens_for_actor(
                actor_id,
                reason="logout_all",
            )
        else:
            await self.token_service.revoke_token(access_token, reason="logout")

        await self.audit_service.log_auth_event(
            AuditEventType.AUTH_LOGOUT,
            actor_id,
            True,
            ip_address,
            metadata={"revoke_all": revoke_all},
        )

        return True
