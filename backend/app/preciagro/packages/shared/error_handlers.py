"""Centralized error handling and sanitization for PreciAgro API.

This module implements secure error response handling that:
- Returns minimal, sanitized error details to clients
- Preserves full error context in internal logs
- Never exposes stack traces, file paths, or internal system details
- Implements consistent error response format across all APIs
"""

import logging
import traceback
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class SanitizedErrorResponse:
    """Sanitized error response that hides internal details from clients."""
    
    def __init__(self, status_code: int, message: str, error_code: str = "INTERNAL_ERROR"):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
    
    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON response."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }


def _sanitize_exception_message(exc: Exception) -> str:
    """Sanitize exception message to prevent information leakage.
    
    Removes:
    - File paths
    - Internal code references
    - Database connection details
    - System configuration details
    """
    message = str(exc)
    
    # Remove file paths
    import re
    message = re.sub(r'[/\\][^\s:]*\.py[^:\s]*:\d+', '<path>', message)
    message = re.sub(r'[a-zA-Z]:[\\/][^\s]*', '<path>', message)
    
    # Remove database credentials
    message = re.sub(
        r'postgresql[+\w]*://[^:]+:[^@]+@[^/]+',
        'postgresql://***:***@***',
        message
    )
    message = re.sub(
        r'(password|secret|key)\s*[:=]\s*["\']?[^"\'\s]+["\']?',
        r'\1=***',
        message,
        flags=re.IGNORECASE
    )
    
    return message


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler that sanitizes responses to clients.
    
    Args:
        request: The incoming request
        exc: The exception that was raised
    
    Returns:
        Sanitized JSON error response
    """
    # Log full exception details internally
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}",
        exc_info=exc,
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client,
        }
    )
    
    # Return sanitized response to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=SanitizedErrorResponse(
            status_code=500,
            message="An internal error occurred. Please try again later.",
            error_code="INTERNAL_ERROR"
        ).to_json()
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with sanitized responses.
    
    Args:
        request: The incoming request
        exc: The validation error
    
    Returns:
        Sanitized validation error response
    """
    # Log validation errors internally
    logger.warning(
        f"Validation error in {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "errors": exc.errors(),
        }
    )
    
    # Return sanitized response (don't expose full validation details)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request data is invalid. Please check your input.",
                "field_count": len(exc.errors())
            }
        }
    )


def add_error_handlers(app: FastAPI, debug: bool = False) -> None:
    """Add global exception handlers to FastAPI application.
    
    Args:
        app: FastAPI application instance
        debug: If True, include more detailed error information (dev only)
    """
    if debug:
        logger.warning("Debug error handling enabled - do NOT use in production")
    
    # Add handlers for common exception types
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    logger.info("Global error handlers registered")
