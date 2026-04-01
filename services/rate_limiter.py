"""
Rate Limiting - Prevent API abuse with Redis-backed rate limiter
"""

from fastapi import Request, HTTPException, status
from typing import Optional, Callable
import redis
import time
import hashlib
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    redis_client = None
    print("⚠️  Redis not available. Rate limiting disabled.")


class RateLimiter:
    """Token bucket rate limiter using Redis"""
    
    def __init__(
        self,
        requests: int = 100,
        window: int = 60,  # seconds
        identifier: str = "global"
    ):
        """
        Initialize rate limiter
        
        Args:
            requests: Max requests allowed in window
            window: Time window in seconds
            identifier: Unique identifier for this limiter
        """
        self.requests = requests
        self.window = window
        self.identifier = identifier
    
    def _get_key(self, client_id: str) -> str:
        """Generate Redis key for client"""
        return f"ratelimit:{self.identifier}:{client_id}"
    
    async def check(self, request: Request) -> bool:
        """
        Check if request is allowed
        
        Returns:
            True if allowed, raises HTTPException if rate limited
        """
        if not REDIS_AVAILABLE:
            return True  # Allow if Redis unavailable
        
        # Get client identifier (IP or user ID)
        client_id = self._get_client_id(request)
        
        key = self._get_key(client_id)
        current = int(time.time())
        window_start = current - self.window
        
        # Remove old entries
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        request_count = redis_client.zcard(key)
        
        if request_count >= self.requests:
            # Get oldest request time to calculate retry-after
            oldest = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1]) + self.window - current
            else:
                retry_after = self.window
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add current request
        redis_client.zadd(key, {str(current): current})
        redis_client.expire(key, self.window)
        
        return True
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request"""
        # Try to get user ID from auth token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            # Hash token to use as identifier
            return hashlib.sha256(token.encode()).hexdigest()[:16]
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return ip


# Predefined rate limiters
GLOBAL_LIMITER = RateLimiter(requests=1000, window=60, identifier="global")
AUTH_LIMITER = RateLimiter(requests=5, window=60, identifier="auth")
AUDIT_LIMITER = RateLimiter(requests=10, window=60, identifier="audit")
API_LIMITER = RateLimiter(requests=100, window=60, identifier="api")


async def rate_limit(
    request: Request,
    limiter: RateLimiter = API_LIMITER
):
    """
    FastAPI dependency for rate limiting
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(
            _: None = Depends(rate_limit)
        ):
            ...
    """
    await limiter.check(request)


# Convenience dependencies
async def rate_limit_global(request: Request):
    await GLOBAL_LIMITER.check(request)


async def rate_limit_auth(request: Request):
    await AUTH_LIMITER.check(request)


async def rate_limit_audit(request: Request):
    await AUDIT_LIMITER.check(request)


def get_rate_limit_info(request: Request, limiter: RateLimiter) -> dict:
    """Get current rate limit status for debugging"""
    if not REDIS_AVAILABLE:
        return {"available": False}
    
    client_id = limiter._get_client_id(request)
    key = limiter._get_key(client_id)
    
    current = int(time.time())
    window_start = current - limiter.window
    
    # Clean old entries
    redis_client.zremrangebyscore(key, 0, window_start)
    
    request_count = redis_client.zcard(key)
    remaining = max(0, limiter.requests - request_count)
    
    return {
        "available": True,
        "limit": limiter.requests,
        "remaining": remaining,
        "reset": current + limiter.window
    }