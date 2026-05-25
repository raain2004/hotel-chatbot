"""Security utilities - JWT authentication & rate limiting."""
import time
import jwt
from typing import Optional
from fastapi import HTTPException, status
from collections import defaultdict
from functools import wraps

from app.config import settings


class JWTAuth:
    """JWT token management for admin authentication."""
    
    algorithm = "HS256"
    
    @staticmethod
    def create_token(subject: str, expires_delta: int = 3600) -> str:
        """Create JWT token for given subject."""
        expire = int(time.time()) + expires_delta
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": int(time.time()),
            "type": "access"
        }
        return jwt.encode(payload, settings.secret_key, algorithm=JWTAuth.algorithm)
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[JWTAuth.algorithm])
            if payload.get("exp", 0) < int(time.time()):
                return None
            return payload
        except jwt.InvalidTokenError:
            return None


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, key: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old requests
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        
        # Check limit
        if len(self._requests[key]) >= max_requests:
            return False
        
        # Record request
        self._requests[key].append(now)
        return True
    
    def get_remaining(self, key: str, max_requests: int = 100, window_seconds: int = 60) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - window_seconds
        current_count = len([t for t in self._requests[key] if t > window_start])
        return max(0, max_requests - current_count)


# Global rate limiter instance
rate_limiter = RateLimiter()


async def verify_jwt_token(authorization: str = None) -> dict:
    """Verify JWT token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    payload = JWTAuth.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload
