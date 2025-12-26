"""Token generation and validation service."""

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

from jose import jwt, JWTError
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Token, TokenType, Actor
from ..core.config import settings


class TokenService:
    """Service for token generation, validation, and management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.JWT_SECRET_KEY
        self.private_key = settings.JWT_PRIVATE_KEY
        self.public_key = settings.JWT_PUBLIC_KEY

    def _get_signing_key(self) -> str:
        """Get the appropriate signing key based on algorithm."""
        if self.algorithm == "RS256":
            if not self.private_key:
                raise ValueError("JWT_PRIVATE_KEY required for RS256")
            return self.private_key
        else:  # HS256
            if not self.secret_key:
                raise ValueError("JWT_SECRET_KEY required for HS256")
            return self.secret_key

    def _get_verification_key(self) -> str:
        """Get the appropriate verification key based on algorithm."""
        if self.algorithm == "RS256":
            if not self.public_key:
                raise ValueError("JWT_PUBLIC_KEY required for RS256")
            return self.public_key
        else:  # HS256
            return self.secret_key

    def _hash_token(self, token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create_access_token(
        self,
        actor_id: str,
        scopes: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> tuple[str, Token]:
        """Create an access token."""
        jti = f"jti_{uuid4().hex[:16]}"
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        expires_at = datetime.now(timezone.utc) + expires_delta

        # Create JWT payload
        payload: Dict[str, Any] = {
            "sub": actor_id,
            "jti": jti,
            "type": "access",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
            "scopes": scopes or [],
        }

        # Sign token
        token_string = jwt.encode(payload, self._get_signing_key(), algorithm=self.algorithm)

        # Store token in database
        token_hash = self._hash_token(token_string)
        token = Token(
            token_id=f"token_{uuid4().hex[:16]}",
            actor_id=actor_id,
            token_type=TokenType.ACCESS,
            token_hash=token_hash,
            jti=jti,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id,
            scopes=scopes or [],
        )

        self.db.add(token)
        await self.db.flush()

        return token_string, token

    async def create_refresh_token(
        self,
        actor_id: str,
        parent_token_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> tuple[str, Token]:
        """Create a refresh token."""
        jti = f"jti_{uuid4().hex[:16]}"
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        expires_at = datetime.now(timezone.utc) + expires_delta

        # Create JWT payload
        payload: Dict[str, Any] = {
            "sub": actor_id,
            "jti": jti,
            "type": "refresh",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
        }

        # Sign token
        token_string = jwt.encode(payload, self._get_signing_key(), algorithm=self.algorithm)

        # Store token in database
        token_hash = self._hash_token(token_string)
        token = Token(
            token_id=f"token_{uuid4().hex[:16]}",
            actor_id=actor_id,
            token_type=TokenType.REFRESH,
            token_hash=token_hash,
            jti=jti,
            expires_at=expires_at,
            parent_token_id=parent_token_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id,
            scopes=[],
        )

        self.db.add(token)
        await self.db.flush()

        return token_string, token

    async def verify_token(self, token_string: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a token."""
        try:
            # Decode JWT
            payload = jwt.decode(
                token_string,
                self._get_verification_key(),
                algorithms=[self.algorithm],
            )

            # Check if token is revoked in database
            jti = payload.get("jti")
            if jti:
                token_hash = self._hash_token(token_string)
                result = await self.db.execute(
                    select(Token).where(
                        and_(
                            or_(Token.token_hash == token_hash, Token.jti == jti),
                            Token.revoked_at.is_(None),
                            Token.expires_at > datetime.now(timezone.utc),
                        )
                    )
                )
                token = result.scalar_one_or_none()
                if not token:
                    return None

            return payload
        except JWTError:
            return None
        except Exception:
            return None

    async def revoke_token(self, token_string: str, reason: Optional[str] = None) -> bool:
        """Revoke a token."""
        token_hash = self._hash_token(token_string)
        result = await self.db.execute(select(Token).where(Token.token_hash == token_hash))
        token = result.scalar_one_or_none()

        if token and not token.revoked_at:
            token.revoked_at = datetime.now(timezone.utc)
            token.revoked_reason = reason
            await self.db.flush()
            return True

        return False

    async def revoke_all_tokens_for_actor(
        self,
        actor_id: str,
        token_type: Optional[TokenType] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Revoke all tokens for an actor."""
        query = select(Token).where(
            and_(
                Token.actor_id == actor_id,
                Token.revoked_at.is_(None),
                Token.expires_at > datetime.now(timezone.utc),
            )
        )

        if token_type:
            query = query.where(Token.token_type == token_type)

        result = await self.db.execute(query)
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            token.revoked_at = datetime.now(timezone.utc)
            token.revoked_reason = reason
            count += 1

        await self.db.flush()
        return count

    async def rotate_refresh_token(
        self,
        old_token_string: str,
        actor_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> tuple[str, Token]:
        """Rotate a refresh token (revoke old, create new)."""
        # Revoke old token
        await self.revoke_token(old_token_string, reason="rotated")

        # Get old token ID for parent reference
        old_token_hash = self._hash_token(old_token_string)
        result = await self.db.execute(select(Token).where(Token.token_hash == old_token_hash))
        old_token = result.scalar_one_or_none()
        parent_token_id = old_token.token_id if old_token else None

        # Create new refresh token
        return await self.create_refresh_token(
            actor_id=actor_id,
            parent_token_id=parent_token_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id,
        )

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens (maintenance task)."""
        result = await self.db.execute(
            select(Token).where(Token.expires_at < datetime.now(timezone.utc))
        )
        tokens = result.scalars().all()
        count = len(tokens)

        for token in tokens:
            await self.db.delete(token)

        await self.db.flush()
        return count
