"""Password hashing and verification service."""

import hashlib
from typing import Optional

try:
    from passlib.context import CryptContext
    from passlib.hash import argon2, bcrypt
    HAS_PASSLIB = True
except ImportError:
    HAS_PASSLIB = False
    import bcrypt as bcrypt_lib

from ..core.config import settings


class PasswordService:
    """Service for password hashing and verification."""
    
    def __init__(self):
        if HAS_PASSLIB and settings.PASSWORD_HASH_ALGORITHM == "argon2id":
            self.context = CryptContext(
                schemes=["argon2"],
                argon2__time_cost=settings.ARGON2_TIME_COST,
                argon2__memory_cost=settings.ARGON2_MEMORY_COST,
                argon2__parallelism=settings.ARGON2_PARALLELISM,
                deprecated="auto",
            )
        else:
            # Fallback to bcrypt
            self.context = CryptContext(
                schemes=["bcrypt"],
                bcrypt__rounds=12,
                deprecated="auto",
            )
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        if not password:
            raise ValueError("Password cannot be empty")
        return self.context.hash(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        if not password or not password_hash:
            return False
        try:
            return self.context.verify(password, password_hash)
        except Exception:
            return False
    
    def needs_rehash(self, password_hash: str) -> bool:
        """Check if password hash needs to be rehashed (algorithm upgrade)."""
        try:
            return self.context.needs_update(password_hash)
        except Exception:
            return True

