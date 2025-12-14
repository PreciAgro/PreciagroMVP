"""Encryption service for data at rest and key management."""

import os
import secrets
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import EncryptionKey
from ..core.config import settings


class EncryptionService:
    """Service for encryption and key management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.algorithm = settings.ENCRYPTION_ALGORITHM
        self.key_rotation_days = settings.KEY_ROTATION_INTERVAL_DAYS
    
    def _generate_key(self) -> bytes:
        """Generate a new encryption key."""
        if self.algorithm == "AES-256-GCM":
            return secrets.token_bytes(32)  # 256 bits
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
    
    def _derive_key_from_master(self, master_key: bytes, key_id: str) -> bytes:
        """Derive a key from master key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=key_id.encode(),
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(master_key)
    
    def _get_master_key(self) -> bytes:
        """Get master key from environment or generate (dev only)."""
        master_key = os.getenv("ENCRYPTION_MASTER_KEY")
        if not master_key:
            if settings.DEV_MODE:
                # Dev mode: use a fixed key (NOT FOR PRODUCTION)
                return b"dev-master-key-32-bytes-long!!"  # 32 bytes
            else:
                raise ValueError("ENCRYPTION_MASTER_KEY must be set in production")
        return master_key.encode() if isinstance(master_key, str) else master_key
    
    async def get_or_create_data_key(self, key_id: str = None) -> Tuple[bytes, EncryptionKey]:
        """Get or create a data encryption key.
        
        Returns:
            Tuple of (decrypted_key_bytes, EncryptionKey model)
        """
        key_id = key_id or settings.ENCRYPTION_KEY_ID
        
        # Try to get active key
        result = await self.db.execute(
            select(EncryptionKey).where(
                and_(
                    EncryptionKey.key_id == key_id,
                    EncryptionKey.key_type == "data_encryption",
                    EncryptionKey.is_active == True,
                    or_(
                        EncryptionKey.expires_at.is_(None),
                        EncryptionKey.expires_at > datetime.now(timezone.utc),
                    ),
                )
            ).order_by(EncryptionKey.key_version.desc())
        )
        key_record = result.scalar_one_or_none()
        
        if key_record:
            # Decrypt the key
            master_key = self._get_master_key()
            decrypted_key = self._decrypt_key(key_record.encrypted_key, master_key, key_id)
            return decrypted_key, key_record
        
        # Create new key
        return await self._create_data_key(key_id)
    
    async def _create_data_key(self, key_id: str) -> Tuple[bytes, EncryptionKey]:
        """Create a new data encryption key."""
        # Generate new key
        new_key = self._generate_key()
        
        # Encrypt with master key (envelope encryption)
        master_key = self._get_master_key()
        encrypted_key = self._encrypt_key(new_key, master_key, key_id)
        
        # Get next version
        result = await self.db.execute(
            select(EncryptionKey).where(EncryptionKey.key_id == key_id)
            .order_by(EncryptionKey.key_version.desc())
        )
        last_key = result.scalar_one_or_none()
        next_version = (last_key.key_version + 1) if last_key else 1
        
        # Deactivate old keys
        if last_key:
            last_key.is_active = False
        
        # Create new key record
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.key_rotation_days)
        key_record = EncryptionKey(
            key_id=key_id,
            key_version=next_version,
            key_type="data_encryption",
            encrypted_key=encrypted_key,
            algorithm=self.algorithm,
            expires_at=expires_at,
        )
        
        self.db.add(key_record)
        await self.db.flush()
        
        return new_key, key_record
    
    def _encrypt_key(self, key: bytes, master_key: bytes, key_id: str) -> bytes:
        """Encrypt a key with master key."""
        # Use AES-GCM for key encryption
        aesgcm = AESGCM(master_key)
        nonce = secrets.token_bytes(12)  # 96 bits for GCM
        ciphertext = aesgcm.encrypt(nonce, key, key_id.encode())
        return nonce + ciphertext
    
    def _decrypt_key(self, encrypted_key: bytes, master_key: bytes, key_id: str) -> bytes:
        """Decrypt a key with master key."""
        nonce = encrypted_key[:12]
        ciphertext = encrypted_key[12:]
        aesgcm = AESGCM(master_key)
        return aesgcm.decrypt(nonce, ciphertext, key_id.encode())
    
    async def encrypt_data(self, data: bytes, key_id: Optional[str] = None) -> Tuple[bytes, str]:
        """Encrypt data using envelope encryption.
        
        Returns:
            Tuple of (encrypted_data, key_id)
        """
        # Get data encryption key
        data_key, key_record = await self.get_or_create_data_key(key_id)
        
        # Encrypt data
        aesgcm = AESGCM(data_key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, data, b"")
        
        # Prepend nonce and key version
        encrypted = nonce + ciphertext
        
        return encrypted, f"{key_record.key_id}:{key_record.key_version}"
    
    async def decrypt_data(self, encrypted_data: bytes, key_reference: str) -> bytes:
        """Decrypt data using envelope encryption.
        
        Args:
            encrypted_data: Encrypted data with nonce prepended
            key_reference: Format "key_id:key_version"
        """
        key_id, key_version_str = key_reference.split(":")
        key_version = int(key_version_str)
        
        # Get key record
        result = await self.db.execute(
            select(EncryptionKey).where(
                and_(
                    EncryptionKey.key_id == key_id,
                    EncryptionKey.key_version == key_version,
                )
            )
        )
        key_record = result.scalar_one_or_none()
        
        if not key_record:
            raise ValueError(f"Key not found: {key_reference}")
        
        # Decrypt the data key
        master_key = self._get_master_key()
        data_key = self._decrypt_key(key_record.encrypted_key, master_key, key_id)
        
        # Decrypt data
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        aesgcm = AESGCM(data_key)
        
        return aesgcm.decrypt(nonce, ciphertext, b"")
    
    async def rotate_key(self, key_id: str) -> EncryptionKey:
        """Rotate an encryption key."""
        # Create new key (this will deactivate old ones)
        _, new_key_record = await self._create_data_key(key_id)
        
        # Mark old key as rotated
        result = await self.db.execute(
            select(EncryptionKey).where(
                and_(
                    EncryptionKey.key_id == key_id,
                    EncryptionKey.is_active == False,
                )
            ).order_by(EncryptionKey.key_version.desc()).limit(1)
        )
        old_key = result.scalar_one_or_none()
        if old_key:
            old_key.rotated_at = datetime.now(timezone.utc)
            await self.db.flush()
        
        return new_key_record
    
    async def get_key_metadata(self, key_id: str) -> Optional[EncryptionKey]:
        """Get key metadata."""
        result = await self.db.execute(
            select(EncryptionKey).where(EncryptionKey.key_id == key_id)
            .order_by(EncryptionKey.key_version.desc())
        )
        return result.scalar_one_or_none()

