"""
Hampstead Renovations - Shared Authentication & Security Module

This module provides:
- API Key authentication
- JWT token authentication (for admin dashboard)
- Rate limiting middleware
- Security utilities

Usage:
    from shared.auth import verify_api_key, require_auth, rate_limit

"""

import os
import time
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any, Callable

import jwt
import structlog
from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

logger = structlog.get_logger()

# API Key configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
VALID_API_KEYS: Dict[str, str] = {}  # key -> service_name mapping

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Security bearer for JWT
bearer_scheme = HTTPBearer(auto_error=False)

# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class TokenData(BaseModel):
    """JWT Token payload data"""
    user_id: str
    email: str
    role: str
    exp: datetime
    iat: datetime


class User(BaseModel):
    """Authenticated user model"""
    id: str
    email: str
    role: str
    name: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# API KEY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def init_api_keys():
    """Initialize API keys from environment variables"""
    global VALID_API_KEYS
    
    # Load API keys from environment
    keys_config = os.getenv("API_KEYS", "")
    if keys_config:
        for key_entry in keys_config.split(","):
            if ":" in key_entry:
                key, service = key_entry.strip().split(":", 1)
                VALID_API_KEYS[key] = service
    
    # Also support individual service keys
    services = ["web-form", "n8n", "internal", "admin"]
    for service in services:
        env_key = f"API_KEY_{service.upper().replace('-', '_')}"
        key = os.getenv(env_key)
        if key:
            VALID_API_KEYS[key] = service
    
    logger.info("api_keys_initialized", count=len(VALID_API_KEYS))


def generate_api_key() -> str:
    """Generate a new secure API key"""
    return f"hr_{secrets.token_urlsafe(32)}"


def verify_api_key(api_key: Optional[str]) -> Optional[str]:
    """
    Verify an API key and return the associated service name.
    Returns None if invalid.
    """
    if not api_key:
        return None
    
    # Constant-time comparison to prevent timing attacks
    for valid_key, service in VALID_API_KEYS.items():
        if hmac.compare_digest(api_key, valid_key):
            return service
    
    return None


async def get_api_key_service(
    api_key: Optional[str] = Security(API_KEY_HEADER)
) -> str:
    """FastAPI dependency for API key authentication"""
    service = verify_api_key(api_key)
    if not service:
        logger.warning("invalid_api_key_attempt", key_prefix=api_key[:10] if api_key else None)
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    return service


# ═══════════════════════════════════════════════════════════════════════════════
# JWT TOKEN MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def create_jwt_token(user: User) -> str:
    """Create a JWT token for a user"""
    now = datetime.utcnow()
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[TokenData]:
    """Verify a JWT token and return the payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenData(
            user_id=payload["user_id"],
            email=payload["email"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
        )
    except jwt.ExpiredSignatureError:
        logger.warning("jwt_expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("jwt_invalid", error=str(e))
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> User:
    """FastAPI dependency for JWT authentication"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = verify_jwt_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return User(
        id=token_data.user_id,
        email=token_data.email,
        role=token_data.role,
    )


def require_role(allowed_roles: list[str]):
    """Dependency factory for role-based access control"""
    async def role_checker(user: User = Security(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimitState:
    """In-memory rate limit state (use Redis in production for distributed systems)"""
    
    def __init__(self):
        self._requests: Dict[str, list[float]] = {}
    
    def is_rate_limited(self, key: str, max_requests: int = RATE_LIMIT_REQUESTS, 
                        window_seconds: int = RATE_LIMIT_WINDOW) -> bool:
        """Check if a key is rate limited"""
        now = time.time()
        window_start = now - window_seconds
        
        # Get existing requests for this key
        requests = self._requests.get(key, [])
        
        # Filter to only requests within the window
        requests = [r for r in requests if r > window_start]
        
        # Check if over limit
        if len(requests) >= max_requests:
            return True
        
        # Add this request
        requests.append(now)
        self._requests[key] = requests
        
        return False
    
    def get_remaining(self, key: str, max_requests: int = RATE_LIMIT_REQUESTS,
                      window_seconds: int = RATE_LIMIT_WINDOW) -> int:
        """Get remaining requests for a key"""
        now = time.time()
        window_start = now - window_seconds
        
        requests = self._requests.get(key, [])
        requests = [r for r in requests if r > window_start]
        
        return max(0, max_requests - len(requests))
    
    def get_reset_time(self, key: str, window_seconds: int = RATE_LIMIT_WINDOW) -> int:
        """Get seconds until rate limit resets"""
        requests = self._requests.get(key, [])
        if not requests:
            return 0
        
        oldest_in_window = min(requests)
        reset_time = oldest_in_window + window_seconds - time.time()
        return max(0, int(reset_time))


# Global rate limit state
_rate_limit_state = RateLimitState()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI applications.
    
    Uses IP address or API key as the rate limit key.
    """
    
    def __init__(self, app, max_requests: int = RATE_LIMIT_REQUESTS, 
                 window_seconds: int = RATE_LIMIT_WINDOW,
                 exclude_paths: Optional[list[str]] = None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Determine rate limit key (prefer API key, fallback to IP)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            rate_key = f"api:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
        else:
            # Get client IP (handle proxies)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else "unknown"
            rate_key = f"ip:{client_ip}"
        
        # Check rate limit
        if _rate_limit_state.is_rate_limited(rate_key, self.max_requests, self.window_seconds):
            remaining = _rate_limit_state.get_remaining(rate_key, self.max_requests, self.window_seconds)
            reset = _rate_limit_state.get_reset_time(rate_key, self.window_seconds)
            
            logger.warning("rate_limit_exceeded", key=rate_key)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Please wait {reset} seconds.",
                    "retry_after": reset,
                },
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(reset),
                }
            )
        
        # Process request and add rate limit headers
        response = await call_next(request)
        
        remaining = _rate_limit_state.get_remaining(rate_key, self.max_requests, self.window_seconds)
        reset = _rate_limit_state.get_reset_time(rate_key, self.window_seconds)
        
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging (e.g., email, phone)"""
    return hashlib.sha256(data.encode()).hexdigest()[:12]


def mask_email(email: str) -> str:
    """Mask email for logging: john.doe@example.com -> j***e@e***.com"""
    if "@" not in email:
        return "***"
    
    local, domain = email.rsplit("@", 1)
    domain_parts = domain.split(".")
    
    masked_local = local[0] + "***" + local[-1] if len(local) > 1 else "***"
    masked_domain = domain_parts[0][0] + "***" if domain_parts else "***"
    
    return f"{masked_local}@{masked_domain}.{domain_parts[-1] if len(domain_parts) > 1 else 'com'}"


def mask_phone(phone: str) -> str:
    """Mask phone for logging: +447123456789 -> +44***6789"""
    digits = ''.join(c for c in phone if c.isdigit() or c == '+')
    if len(digits) < 4:
        return "***"
    return digits[:3] + "***" + digits[-4:]


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

# Initialize API keys on module load
init_api_keys()
