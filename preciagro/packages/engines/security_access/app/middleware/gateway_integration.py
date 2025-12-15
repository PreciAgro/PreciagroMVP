"""API Gateway integration middleware."""

from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from ..services.token_service import TokenService
from ..services.authorization_service import AuthorizationService
from ..services.audit_service import AuditService
from ..db.base import get_db
from ..db.models import AuditEventType
import logging

logger = logging.getLogger(__name__)


class SecurityGatewayMiddleware(BaseHTTPMiddleware):
    """Middleware for API Gateway integration.

    This middleware:
    1. Validates authentication tokens
    2. Performs authorization checks
    3. Logs security events
    4. Adds security context to request
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware."""
        # Skip security for health checks and public endpoints
        if request.url.path in ["/health", "/", "/v1/health"]:
            return await call_next(request)

        # Get token from Authorization header
        authorization = request.headers.get("Authorization")
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]

        # Get database session
        async for db in get_db():
            try:
                # Verify token if present
                actor_id = None
                if token:
                    token_service = TokenService(db)
                    payload = await token_service.verify_token(token)
                    if payload:
                        actor_id = payload.get("sub")

                # Add security context to request state
                request.state.actor_id = actor_id
                request.state.token = token
                request.state.authenticated = actor_id is not None

                # Process request
                response = await call_next(request)

                # Log security event if needed
                if actor_id and request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                    audit_service = AuditService(db)
                    await audit_service.log_data_access(
                        actor_id=actor_id,
                        resource_type=(
                            request.url.path.split("/")[1]
                            if len(request.url.path.split("/")) > 1
                            else "unknown"
                        ),
                        resource_id=None,
                        action=request.method.lower(),
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("User-Agent"),
                    )

                return response

            except Exception as e:
                logger.error(f"Security middleware error: {e}")
                # In case of error, allow request to proceed (fail open for availability)
                # In production, you might want to fail closed
                return await call_next(request)
            finally:
                break


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware for route-level authorization."""

    def __init__(self, app, required_permission: Optional[str] = None):
        super().__init__(app)
        self.required_permission = required_permission

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check authorization before processing request."""
        if not hasattr(request.state, "actor_id") or not request.state.actor_id:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
            )

        if self.required_permission:
            async for db in get_db():
                try:
                    # Parse permission (format: "resource:action")
                    parts = self.required_permission.split(":", 1)
                    resource = parts[0]
                    action = parts[1] if len(parts) > 1 else "read"

                    authz_service = AuthorizationService(db)
                    allowed = await authz_service.check_permission(
                        request.state.actor_id,
                        resource,
                        action,
                        context={
                            "ip_address": request.client.host if request.client else None,
                            "user_agent": request.headers.get("User-Agent"),
                        },
                    )

                    if not allowed:
                        audit_service = AuditService(db)
                        await audit_service.log_permission_event(
                            request.state.actor_id,
                            resource,
                            None,
                            action,
                            False,
                            request.client.host if request.client else None,
                        )

                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={"detail": "Permission denied"},
                        )

                    return await call_next(request)
                finally:
                    break

        return await call_next(request)


def require_permission(permission: str):
    """Decorator factory for requiring permissions on routes."""

    def decorator(func):
        # This would be used with FastAPI dependencies
        # For now, it's a placeholder
        return func

    return decorator
