"""Shared input validation utilities and middleware."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# Request size limit middleware
class RequestSizeLimitMiddleware:
    """Middleware to limit request body size."""
    
    def __init__(self, app: FastAPI, max_size: int = 10 * 1024 * 1024):  # 10MB default
        self.app = app
        self.max_size = max_size
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check content-length header
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        
        if content_length:
            try:
                size = int(content_length.decode())
                if size > self.max_size:
                    response = JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": 413,
                                "message": f"Request body too large. Maximum size: {self.max_size} bytes",
                            }
                        },
                    )
                    await response(scope, receive, send)
                    return
            except (ValueError, UnicodeDecodeError):
                pass
        
        await self.app(scope, receive, send)


def add_request_size_limit(app: FastAPI, max_size: int = 10 * 1024 * 1024) -> None:
    """Add request size limit middleware to app.
    
    Args:
        app: FastAPI application
        max_size: Maximum request size in bytes (default 10MB)
    """
    app.add_middleware(RequestSizeLimitMiddleware, max_size=max_size)
    logger.info(f"Request size limit middleware added: {max_size} bytes")


# Common validation models
class HealthResponse(BaseModel):
    """Standard health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: float = Field(..., description="Response timestamp")


class ErrorDetail(BaseModel):
    """Standard error detail."""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: str | None = Field(None, description="Field that caused the error")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(1, ge=1, le=1000, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @validator("page_size")
    def validate_page_size(cls, v):
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


# Content-type validation
ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
}


async def validate_content_type(request: Request, call_next: Callable) -> Response:
    """Middleware to validate request content-type.
    
    Only applies to POST, PUT, PATCH requests with body.
    """
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("content-type", "").split(";")[0]
        
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={
                    "error": {
                        "code": 415,
                        "message": f"Unsupported media type: {content_type}",
                        "allowed": list(ALLOWED_CONTENT_TYPES),
                    }
                },
            )
    
    return await call_next(request)


# Input sanitization helpers
def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input by trimming and limiting length.
    
    Args:
        value: Input string
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)
    
    # Trim whitespace
    value = value.strip()
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    return value


def sanitize_email(email: str) -> str:
    """Basic email sanitization.
    
    Args:
        email: Email address
    
    Returns:
        Lowercase, trimmed email
    """
    return email.lower().strip()
