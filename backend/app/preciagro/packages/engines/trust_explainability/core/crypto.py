"""Cryptographic Signing for Audit Compliance.

Provides immutable trace verification through digital signatures.
"""

import hashlib
import hmac
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass

from ..contracts.v1.schemas import ReasoningTrace

logger = logging.getLogger(__name__)


@dataclass
class SignedTrace:
    """A signed reasoning trace."""

    trace_id: str
    signature: str
    algorithm: str
    signed_at: datetime
    key_id: str

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "signature": self.signature,
            "algorithm": self.algorithm,
            "signed_at": self.signed_at.isoformat(),
            "key_id": self.key_id,
        }


@dataclass
class VerificationResult:
    """Result of signature verification."""

    valid: bool
    trace_id: str
    verified_at: datetime
    message: str
    key_id: Optional[str] = None


class KeyProvider(ABC):
    """Abstract key provider for cryptographic operations.

    Implementations can use local files, HSM, or cloud KMS.
    """

    @abstractmethod
    def get_signing_key(self) -> bytes:
        """Get the current signing key."""
        pass

    @abstractmethod
    def get_key_id(self) -> str:
        """Get identifier for the current key."""
        pass

    @abstractmethod
    def get_verification_key(self, key_id: str) -> Optional[bytes]:
        """Get a verification key by ID."""
        pass


class LocalKeyProvider(KeyProvider):
    """File-based key provider for development/testing.

    In production, use HSM or cloud KMS.
    """

    def __init__(self, key_path: Optional[str] = None, key_id: str = "local-dev-key") -> None:
        """Initialize local key provider.

        Args:
            key_path: Path to key file (generates if not exists)
            key_id: Identifier for this key
        """
        self._key_id = key_id
        self._key_path = key_path or self._default_key_path()
        self._key: Optional[bytes] = None
        self._load_or_generate_key()

    def get_signing_key(self) -> bytes:
        """Get the signing key."""
        if self._key is None:
            self._load_or_generate_key()
        return self._key  # type: ignore

    def get_key_id(self) -> str:
        """Get key identifier."""
        return self._key_id

    def get_verification_key(self, key_id: str) -> Optional[bytes]:
        """Get verification key by ID."""
        if key_id == self._key_id:
            return self.get_signing_key()
        return None

    def _default_key_path(self) -> str:
        """Get default key path."""
        # Use temp directory for dev
        import tempfile

        return os.path.join(tempfile.gettempdir(), "tee_signing_key.bin")

    def _load_or_generate_key(self) -> None:
        """Load key from file or generate new one."""
        try:
            if os.path.exists(self._key_path):
                with open(self._key_path, "rb") as f:
                    self._key = f.read()
                logger.info(f"Loaded signing key from {self._key_path}")
            else:
                # Generate new 256-bit key
                self._key = os.urandom(32)
                with open(self._key_path, "wb") as f:
                    f.write(self._key)
                logger.info(f"Generated new signing key at {self._key_path}")
        except Exception as e:
            logger.warning(f"Key file error: {e}. Using ephemeral key.")
            self._key = os.urandom(32)


class EnvironmentKeyProvider(KeyProvider):
    """Key provider using environment variables.

    Suitable for container deployments.
    """

    def __init__(
        self, key_env_var: str = "TEE_SIGNING_KEY", key_id_env_var: str = "TEE_SIGNING_KEY_ID"
    ) -> None:
        """Initialize environment key provider.

        Args:
            key_env_var: Environment variable containing hex-encoded key
            key_id_env_var: Environment variable containing key ID
        """
        self._key_env_var = key_env_var
        self._key_id_env_var = key_id_env_var

    def get_signing_key(self) -> bytes:
        """Get signing key from environment."""
        key_hex = os.environ.get(self._key_env_var)
        if not key_hex:
            raise ValueError(f"Environment variable {self._key_env_var} not set")
        return bytes.fromhex(key_hex)

    def get_key_id(self) -> str:
        """Get key ID from environment."""
        return os.environ.get(self._key_id_env_var, "env-key")

    def get_verification_key(self, key_id: str) -> Optional[bytes]:
        """Get verification key."""
        if key_id == self.get_key_id():
            return self.get_signing_key()
        return None


class TraceSigner:
    """Signs and verifies reasoning traces for audit compliance.

    Uses HMAC-SHA256 for signing. In production with HSM,
    could use RSA or ECDSA.
    """

    def __init__(self, key_provider: Optional[KeyProvider] = None) -> None:
        """Initialize trace signer.

        Args:
            key_provider: Key provider instance (defaults to LocalKeyProvider)
        """
        self._key_provider = key_provider or LocalKeyProvider()
        logger.info(f"TraceSigner initialized with key ID: {self._key_provider.get_key_id()}")

    def sign(self, trace: ReasoningTrace) -> SignedTrace:
        """Sign a reasoning trace.

        Args:
            trace: Trace to sign

        Returns:
            SignedTrace with signature
        """
        # Serialize trace to canonical JSON
        canonical = self._canonicalize(trace)

        # Get signing key
        key = self._key_provider.get_signing_key()
        key_id = self._key_provider.get_key_id()

        # Generate HMAC-SHA256 signature
        signature = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

        signed = SignedTrace(
            trace_id=trace.trace_id,
            signature=signature,
            algorithm="HMAC-SHA256",
            signed_at=datetime.utcnow(),
            key_id=key_id,
        )

        logger.debug(f"Signed trace {trace.trace_id}")
        return signed

    def verify(
        self, trace: ReasoningTrace, signature: str, key_id: Optional[str] = None
    ) -> VerificationResult:
        """Verify a trace signature.

        Args:
            trace: Trace to verify
            signature: Signature to check
            key_id: Optional key ID (uses current key if not specified)

        Returns:
            VerificationResult
        """
        try:
            # Get verification key
            kid = key_id or self._key_provider.get_key_id()
            key = self._key_provider.get_verification_key(kid)

            if key is None:
                return VerificationResult(
                    valid=False,
                    trace_id=trace.trace_id,
                    verified_at=datetime.utcnow(),
                    message=f"Unknown key ID: {kid}",
                    key_id=kid,
                )

            # Recompute signature
            canonical = self._canonicalize(trace)
            expected = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

            # Compare
            valid = hmac.compare_digest(signature, expected)

            return VerificationResult(
                valid=valid,
                trace_id=trace.trace_id,
                verified_at=datetime.utcnow(),
                message="Signature valid" if valid else "Signature mismatch",
                key_id=kid,
            )

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return VerificationResult(
                valid=False,
                trace_id=trace.trace_id,
                verified_at=datetime.utcnow(),
                message=f"Verification error: {str(e)}",
            )

    def _canonicalize(self, trace: ReasoningTrace) -> str:
        """Create canonical JSON representation for signing.

        Args:
            trace: Trace to canonicalize

        Returns:
            Canonical JSON string
        """
        # Exclude signature-related fields
        trace_dict = trace.model_dump(exclude={"signature", "signature_algorithm"}, mode="json")

        # Sort keys for deterministic output
        return json.dumps(trace_dict, sort_keys=True, default=str)

    def get_key_id(self) -> str:
        """Get current key ID."""
        return self._key_provider.get_key_id()


# Singleton instance
_signer: Optional[TraceSigner] = None


def get_trace_signer() -> TraceSigner:
    """Get singleton trace signer instance."""
    global _signer
    if _signer is None:
        _signer = TraceSigner()
    return _signer
