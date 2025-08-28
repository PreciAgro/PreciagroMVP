"""Authentication and authorization for temporal logic engine."""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from ..config import config

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails."""
    pass


class TokenManager:
    """Manages JWT tokens for API authentication."""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or config.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = config.access_token_expire_minutes
    
    def create_access_token(
        self, 
        subject: str, 
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Created access token for {subject}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise AuthenticationError("Failed to create access token")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != "access":
                raise AuthenticationError("Invalid token type")
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise AuthenticationError("Token expired")
            
            return payload
        
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise AuthenticationError("Invalid token")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise AuthenticationError("Token verification failed")
    
    def get_subject_from_token(self, token: str) -> str:
        """Extract subject from token."""
        payload = self.verify_token(token)
        return payload.get("sub")


class PasswordManager:
    """Manages password hashing and verification."""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)


class Permission:
    """Represents a permission in the system."""
    
    # Rule permissions
    READ_RULES = "rules:read"
    CREATE_RULES = "rules:create"
    UPDATE_RULES = "rules:update"
    DELETE_RULES = "rules:delete"
    
    # Event permissions
    CREATE_EVENTS = "events:create"
    READ_EVENTS = "events:read"
    
    # Task permissions
    READ_TASKS = "tasks:read"
    UPDATE_TASKS = "tasks:update"
    CANCEL_TASKS = "tasks:cancel"
    
    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"
    
    # Channel permissions
    SEND_WHATSAPP = "channels:whatsapp:send"
    SEND_SMS = "channels:sms:send"
    SEND_EMAIL = "channels:email:send"
    
    @classmethod
    def get_all_permissions(cls) -> List[str]:
        """Get list of all permissions."""
        return [
            cls.READ_RULES, cls.CREATE_RULES, cls.UPDATE_RULES, cls.DELETE_RULES,
            cls.CREATE_EVENTS, cls.READ_EVENTS,
            cls.READ_TASKS, cls.UPDATE_TASKS, cls.CANCEL_TASKS,
            cls.ADMIN_USERS, cls.ADMIN_SYSTEM,
            cls.SEND_WHATSAPP, cls.SEND_SMS, cls.SEND_EMAIL
        ]


class Role:
    """Represents a role with permissions."""
    
    ADMIN = {
        "name": "admin",
        "permissions": Permission.get_all_permissions()
    }
    
    OPERATOR = {
        "name": "operator",
        "permissions": [
            Permission.READ_RULES, Permission.UPDATE_RULES,
            Permission.CREATE_EVENTS, Permission.READ_EVENTS,
            Permission.READ_TASKS, Permission.UPDATE_TASKS,
            Permission.SEND_WHATSAPP, Permission.SEND_SMS, Permission.SEND_EMAIL
        ]
    }
    
    VIEWER = {
        "name": "viewer",
        "permissions": [
            Permission.READ_RULES, Permission.READ_EVENTS, Permission.READ_TASKS
        ]
    }
    
    SERVICE = {
        "name": "service",
        "permissions": [
            Permission.CREATE_EVENTS, Permission.READ_EVENTS,
            Permission.READ_TASKS, Permission.UPDATE_TASKS
        ]
    }
    
    @classmethod
    def get_role_permissions(cls, role_name: str) -> List[str]:
        """Get permissions for a role."""
        roles = {
            "admin": cls.ADMIN["permissions"],
            "operator": cls.OPERATOR["permissions"],
            "viewer": cls.VIEWER["permissions"],
            "service": cls.SERVICE["permissions"]
        }
        return roles.get(role_name, [])


class AuthorizationManager:
    """Manages authorization and permissions."""
    
    def __init__(self):
        self.user_roles: Dict[str, List[str]] = {}
        self.user_permissions: Dict[str, List[str]] = {}
    
    def assign_role(self, user_id: str, role_name: str):
        """Assign a role to a user."""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
        
        if role_name not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role_name)
            logger.info(f"Assigned role '{role_name}' to user {user_id}")
    
    def remove_role(self, user_id: str, role_name: str):
        """Remove a role from a user."""
        if user_id in self.user_roles and role_name in self.user_roles[user_id]:
            self.user_roles[user_id].remove(role_name)
            logger.info(f"Removed role '{role_name}' from user {user_id}")
    
    def grant_permission(self, user_id: str, permission: str):
        """Grant a specific permission to a user."""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = []
        
        if permission not in self.user_permissions[user_id]:
            self.user_permissions[user_id].append(permission)
            logger.info(f"Granted permission '{permission}' to user {user_id}")
    
    def revoke_permission(self, user_id: str, permission: str):
        """Revoke a specific permission from a user."""
        if user_id in self.user_permissions and permission in self.user_permissions[user_id]:
            self.user_permissions[user_id].remove(permission)
            logger.info(f"Revoked permission '{permission}' from user {user_id}")
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user (from roles and direct grants)."""
        permissions = set()
        
        # Add permissions from roles
        for role_name in self.user_roles.get(user_id, []):
            role_permissions = Role.get_role_permissions(role_name)
            permissions.update(role_permissions)
        
        # Add direct permissions
        user_perms = self.user_permissions.get(user_id, [])
        permissions.update(user_perms)
        
        return list(permissions)
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission."""
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions
    
    def require_permission(self, user_id: str, permission: str):
        """Require user to have permission, raise exception if not."""
        if not self.has_permission(user_id, permission):
            logger.warning(f"User {user_id} denied access: missing permission '{permission}'")
            raise AuthorizationError(f"Missing permission: {permission}")
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get all roles assigned to a user."""
        return self.user_roles.get(user_id, [])


class SecurityMiddleware:
    """Security middleware for API endpoints."""
    
    def __init__(self):
        self.token_manager = TokenManager()
        self.auth_manager = AuthorizationManager()
        self.session_store: Dict[str, Dict[str, Any]] = {}
    
    def authenticate_token(self, authorization_header: str) -> Dict[str, Any]:
        """Authenticate using Bearer token."""
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise AuthenticationError("Missing or invalid authorization header")
        
        token = authorization_header[7:]  # Remove "Bearer " prefix
        payload = self.token_manager.verify_token(token)
        
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        
        return {
            "user_id": user_id,
            "token_payload": payload
        }
    
    def authenticate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Authenticate using API key (for service accounts)."""
        # In a real implementation, you'd validate against a database
        # For now, we'll use a simple check
        if not api_key or len(api_key) < 32:
            raise AuthenticationError("Invalid API key")
        
        # Mock validation - in production, check against database
        service_accounts = {
            "sk_test_temporal_engine_api_key_12345": "temporal_engine_service",
            "sk_prod_data_integration_api_key_67890": "data_integration_service"
        }
        
        if api_key not in service_accounts:
            raise AuthenticationError("Invalid API key")
        
        service_name = service_accounts[api_key]
        
        # Assign service role
        self.auth_manager.assign_role(service_name, "service")
        
        return {
            "user_id": service_name,
            "auth_type": "api_key"
        }
    
    def authorize_request(self, user_id: str, required_permission: str):
        """Authorize a request."""
        self.auth_manager.require_permission(user_id, required_permission)
    
    def create_session(self, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a user session."""
        import secrets
        session_id = secrets.token_urlsafe(32)
        
        self.session_store[session_id] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return self.session_store.get(session_id)
    
    def invalidate_session(self, session_id: str):
        """Invalidate a session."""
        if session_id in self.session_store:
            del self.session_store[session_id]


# Global instances
security_middleware = SecurityMiddleware()
token_manager = TokenManager()
password_manager = PasswordManager()

# Setup default admin user
security_middleware.auth_manager.assign_role("admin", "admin")
security_middleware.auth_manager.assign_role("system", "service")
