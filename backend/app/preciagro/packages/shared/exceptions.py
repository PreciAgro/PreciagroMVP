"""PreciAgro custom exception hierarchy for precise error handling.

This module defines a complete exception hierarchy that enables:
- Specific exception handling instead of broad 'except Exception'
- Structured error context and logging
- Proper error propagation semantics
- Clear distinction between recoverable and fatal errors
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels for operational decisions."""
    RECOVERABLE = "recoverable"  # Transient, can retry
    DEGRADED = "degraded"  # Service works partially
    FATAL = "fatal"  # Must fail fast


class PreciAgroException(Exception):
    """Base exception for all PreciAgro errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        severity: ErrorSeverity = ErrorSeverity.FATAL,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize exception with structured context.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error identifier
            severity: Whether this is recoverable or fatal
            context: Additional structured context for logging
            cause: The underlying exception that triggered this
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        """String representation includes code and context."""
        parts = [f"[{self.error_code}]", self.message]
        if self.context:
            parts.append(f"context={self.context}")
        return " ".join(parts)

    def log(self, logger_instance=None, level=logging.ERROR) -> None:
        """Log the exception with full context.

        Args:
            logger_instance: Logger to use (defaults to module logger)
            level: Logging level (default ERROR)
        """
        log = logger_instance or logger
        log.log(
            level,
            f"{self}",
            exc_info=self.cause,
            extra={
                "error_code": self.error_code,
                "severity": self.severity.value,
                "context": self.context,
            },
        )


# ========== INPUT VALIDATION ERRORS ==========

class ValidationError(PreciAgroException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        if field:
            context["field"] = field
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.RECOVERABLE,
            context=context,
            cause=cause,
        )


class InvalidGeoPolygonError(ValidationError):
    """Raised when geo polygon is invalid."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            context=context or {},
            field="polygon",
        )


class InvalidCoordinateError(ValidationError):
    """Raised when coordinates are invalid."""

    def __init__(
        self, lat: float = None, lon: float = None, context: Optional[Dict[str, Any]] = None
    ):
        context = context or {}
        if lat is not None:
            context["latitude"] = lat
        if lon is not None:
            context["longitude"] = lon

        super().__init__(
            message=f"Invalid coordinates: lat={lat}, lon={lon}",
            context=context,
            field="coordinates",
        )


class InvalidDateRangeError(ValidationError):
    """Raised when date range is invalid."""

    def __init__(
        self,
        start_date: str = None,
        end_date: str = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        context = context or {}
        if start_date:
            context["start_date"] = start_date
        if end_date:
            context["end_date"] = end_date

        super().__init__(
            message=f"Invalid date range: {start_date} to {end_date}",
            context=context,
            field="date_range",
        )


class InvalidNumericThresholdError(ValidationError):
    """Raised when numeric threshold is invalid."""

    def __init__(
        self,
        parameter: str,
        value: float = None,
        min_val: float = None,
        max_val: float = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        context = context or {}
        context["parameter"] = parameter
        if value is not None:
            context["value"] = value
        if min_val is not None:
            context["min"] = min_val
        if max_val is not None:
            context["max"] = max_val

        super().__init__(
            message=f"Invalid threshold for {parameter}: {value} (expected {min_val}-{max_val})",
            context=context,
            field=parameter,
        )


# ========== AUTHENTICATION & AUTHORIZATION ERRORS ==========

class AuthenticationError(PreciAgroException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            severity=ErrorSeverity.RECOVERABLE,
            context=context or {},
            cause=cause,
        )


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid or expired."""

    def __init__(self, reason: str = "Invalid token", context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Token validation failed: {reason}",
            context=context or {"reason": reason},
        )


class TokenExpiredError(AuthenticationError):
    """Raised when token has expired."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Token has expired",
            context=context or {},
        )


class AuthorizationError(PreciAgroException):
    """Raised when user lacks required permissions."""

    def __init__(
        self,
        message: str,
        required_scopes: list = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        context = context or {}
        if required_scopes:
            context["required_scopes"] = required_scopes
        super().__init__(
            message=message,
            error_code="AUTHZ_ERROR",
            severity=ErrorSeverity.RECOVERABLE,
            context=context,
        )


# ========== RATE LIMITING & QUOTA ERRORS ==========

class RateLimitExceededError(PreciAgroException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: int,
        window_seconds: int = 60,
        context: Optional[Dict[str, Any]] = None,
    ):
        context = context or {}
        context["limit"] = limit
        context["window_seconds"] = window_seconds

        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window_seconds}s",
            error_code="RATE_LIMIT_ERROR",
            severity=ErrorSeverity.RECOVERABLE,
            context=context,
        )


class QuotaExceededError(PreciAgroException):
    """Raised when quota is exceeded."""

    def __init__(
        self,
        resource: str,
        quota: int,
        used: int,
        context: Optional[Dict[str, Any]] = None,
    ):
        context = context or {}
        context["resource"] = resource
        context["quota"] = quota
        context["used"] = used

        super().__init__(
            message=f"Quota exceeded for {resource}: {used}/{quota}",
            error_code="QUOTA_ERROR",
            severity=ErrorSeverity.RECOVERABLE,
            context=context,
        )


# ========== DATA & STORAGE ERRORS ==========

class DataError(PreciAgroException):
    """Raised for data access or integrity errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="DATA_ERROR",
            severity=ErrorSeverity.FATAL,
            context=context or {},
            cause=cause,
        )


class DatabaseError(DataError):
    """Raised when database operation fails."""

    def __init__(
        self,
        message: str,
        operation: str = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        if operation:
            context["operation"] = operation
        super().__init__(
            message=f"Database error: {message}",
            context=context,
            cause=cause,
        )


class ConnectionError(DataError):
    """Raised when external service connection fails."""

    def __init__(
        self,
        service: str,
        message: str = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        context["service"] = service
        msg = message or f"Failed to connect to {service}"
        super().__init__(
            message=msg,
            context=context,
            cause=cause,
        )


class TimeoutError(DataError):
    """Raised when operation times out."""

    def __init__(
        self,
        operation: str,
        timeout_seconds: float = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        context["operation"] = operation
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=f"Operation '{operation}' timed out",
            context=context,
            cause=cause,
        )


# ========== CONFIGURATION ERRORS ==========

class ConfigurationError(PreciAgroException):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        config_key: str = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        if config_key:
            context["config_key"] = config_key
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            severity=ErrorSeverity.FATAL,
            context=context,
            cause=cause,
        )


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    def __init__(self, keys: list, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        context["missing_keys"] = keys
        super().__init__(
            message=f"Missing required configuration: {', '.join(keys)}",
            context=context,
        )


# ========== ENGINE EXECUTION ERRORS ==========

class EngineError(PreciAgroException):
    """Raised when engine execution fails."""

    def __init__(
        self,
        engine_name: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        context["engine"] = engine_name
        super().__init__(
            message=f"{engine_name} engine error: {message}",
            error_code="ENGINE_ERROR",
            severity=ErrorSeverity.DEGRADED,
            context=context,
            cause=cause,
        )


class GeoContextError(EngineError):
    """Raised when geo context engine fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            engine_name="GeoContext",
            message=message,
            context=context or {},
            cause=cause,
        )


class TemporalLogicError(EngineError):
    """Raised when temporal logic engine fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            engine_name="TemporalLogic",
            message=message,
            context=context or {},
            cause=cause,
        )


class DataIntegrationError(EngineError):
    """Raised when data integration engine fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            engine_name="DataIntegration",
            message=message,
            context=context or {},
            cause=cause,
        )


class ExternalAPIError(EngineError):
    """Raised when external API call fails."""

    def __init__(
        self,
        api_name: str,
        status_code: int = None,
        message: str = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        context = context or {}
        context["api"] = api_name
        if status_code:
            context["status_code"] = status_code
        msg = message or f"External API '{api_name}' returned error"
        super().__init__(
            engine_name="DataIntegration",
            message=msg,
            context=context,
            cause=cause,
        )


# ========== UTILITY FUNCTIONS ==========

def is_recoverable(exc: Exception) -> bool:
    """Determine if an exception is recoverable (safe to retry).

    Args:
        exc: Exception to check

    Returns:
        True if exception is marked as recoverable
    """
    if isinstance(exc, PreciAgroException):
        return exc.severity == ErrorSeverity.RECOVERABLE
    # External exceptions are assumed not recoverable
    return False


def get_error_response(exc: Exception) -> Dict[str, Any]:
    """Convert exception to standardized error response.

    Args:
        exc: Exception to convert

    Returns:
        Dictionary with error, code, and message
    """
    if isinstance(exc, PreciAgroException):
        return {
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "severity": exc.severity.value,
                "context": exc.context,
            }
        }
    # Sanitize unknown exceptions
    return {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "severity": ErrorSeverity.FATAL.value,
        }
    }
