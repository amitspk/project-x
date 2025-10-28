"""
Rate limiting for the Blog Manager API.

Implements per-IP and per-endpoint rate limiting to protect against abuse.
Uses SlowAPI for FastAPI integration.
"""

import logging
from typing import Callable, Optional
from functools import wraps

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

logger = logging.getLogger(__name__)


def get_identifier(request: Request) -> str:
    """
    Get a unique identifier for rate limiting.
    
    Priority:
    1. API key (if authentication is enabled)
    2. User ID (if authenticated)
    3. IP address (fallback)
    
    Args:
        request: FastAPI request object
        
    Returns:
        Unique identifier string
    """
    # Check for API key in header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"
    
    # Check for authenticated user (future auth implementation)
    user_id = request.state.__dict__.get("user_id")
    if user_id:
        return f"user:{user_id}"
    
    # Fallback to IP address
    return f"ip:{get_remote_address(request)}"


# Create limiter instance
limiter = Limiter(
    key_func=get_identifier,
    default_limits=["100/minute", "1000/hour", "5000/day"],  # Global defaults
    storage_uri="memory://",  # Use in-memory storage (upgrade to Redis for production)
    strategy="fixed-window",  # or "moving-window" for more accuracy
    headers_enabled=True,  # Add rate limit headers to responses
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Provides user-friendly error messages with retry information.
    """
    # Extract rate limit info
    limit = exc.detail.split(":")[-1].strip() if ":" in exc.detail else exc.detail
    
    logger.warning(
        f"Rate limit exceeded for {get_identifier(request)}. "
        f"Endpoint: {request.url.path}. Limit: {limit}"
    )
    
    # Build custom response
    response_data = {
        "error": "rate_limit_exceeded",
        "message": "Too many requests. Please slow down and try again later.",
        "details": {
            "limit": limit,
            "endpoint": request.url.path,
            "identifier": get_identifier(request).split(":")[0]  # Just show type, not value
        }
    }
    
    # Get retry-after from headers if available
    retry_after = getattr(exc, "retry_after", None)
    if retry_after:
        response_data["retry_after_seconds"] = retry_after
    
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content=response_data,
        headers={
            "Retry-After": str(retry_after) if retry_after else "60"
        }
    )


# Rate limit configurations for different endpoint categories
class RateLimits:
    """Pre-defined rate limits for different types of endpoints."""
    
    # Expensive AI operations
    AI_GENERATION = "10/minute"  # Q&A, question generation
    AI_EMBEDDING = "20/minute"   # Embedding generation
    
    # Standard API operations
    READ_OPERATIONS = "100/minute"  # GET requests
    WRITE_OPERATIONS = "30/minute"  # POST/PUT/DELETE
    
    # Search and lookup
    SEARCH = "50/minute"
    SIMILARITY_SEARCH = "20/minute"
    
    # Health and monitoring (very permissive)
    HEALTH_CHECK = "1000/minute"
    
    # Authentication (protect from brute force)
    AUTH_LOGIN = "5/minute"
    AUTH_REGISTER = "3/minute"


def apply_rate_limit(limit: str):
    """
    Decorator to apply rate limiting to a FastAPI endpoint.
    
    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")
    
    Example:
        @app.get("/api/v1/expensive-operation")
        @apply_rate_limit("5/minute")
        async def expensive_operation():
            return {"result": "data"}
    """
    def decorator(func: Callable) -> Callable:
        # Apply the limiter decorator
        return limiter.limit(limit)(func)
    return decorator


def get_rate_limit_status(request: Request) -> dict:
    """
    Get current rate limit status for a request.
    
    Useful for monitoring and debugging.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with rate limit information
    """
    identifier = get_identifier(request)
    
    # Note: SlowAPI doesn't expose internal state easily
    # This is a simplified version
    return {
        "identifier": identifier.split(":")[0],  # Type only (ip/user/api_key)
        "limits": limiter.default_limits,
        "storage": "memory",  # or "redis" in production
        "strategy": "fixed-window"
    }


# Middleware to add rate limit headers to all responses
async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to add rate limit information to response headers.
    
    Headers added:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Requests remaining
    - X-RateLimit-Reset: Time when limit resets
    """
    response = await call_next(request)
    
    # Note: SlowAPI automatically adds these headers when headers_enabled=True
    # This middleware is here for additional customization if needed
    
    return response


def configure_redis_backend(redis_url: str):
    """
    Configure Redis as the storage backend for rate limiting.
    
    Use this in production for distributed rate limiting across multiple instances.
    
    Args:
        redis_url: Redis connection URL (e.g., "redis://localhost:6379")
    
    Example:
        configure_redis_backend("redis://localhost:6379")
    """
    global limiter
    limiter = Limiter(
        key_func=get_identifier,
        default_limits=["100/minute", "1000/hour", "5000/day"],
        storage_uri=redis_url,
        strategy="fixed-window",
        headers_enabled=True,
    )
    logger.info(f"Rate limiting configured with Redis backend: {redis_url}")


def get_limiter() -> Limiter:
    """Get the global limiter instance."""
    return limiter

