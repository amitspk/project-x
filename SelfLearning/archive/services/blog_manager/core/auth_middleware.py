"""
Authentication middleware for FastAPI.

Handles API key extraction, validation, and injection into request state.
"""

import logging
from typing import Optional, List, Callable
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader

from .auth import APIKeyManager, APIKeyScope, check_scope, AuthenticationError, AuthorizationError
from ..data.api_key_repository import APIKeyRepository
from ..data.database import db_manager

logger = logging.getLogger(__name__)

# API Key header extractor
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthenticationMiddleware:
    """
    Middleware to handle API key authentication.
    
    Extracts API key from X-API-Key header, validates it, and injects
    user information into request.state for downstream use.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Process request
        request = Request(scope, receive)
        
        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        
        # If no API key, continue without authentication
        # (We'll enforce it per-endpoint using dependencies)
        if not api_key:
            await self.app(scope, receive, send)
            return
        
        # Validate API key
        try:
            api_key_repo = APIKeyRepository(db_manager.database)
            
            # Find all active keys and validate
            # (In production, optimize this with caching)
            active_keys = await api_key_repo.find_all_active(limit=1000)
            
            authenticated = False
            for stored_key in active_keys:
                if APIKeyManager.verify_key(api_key, stored_key.hashed_key):
                    # Check if key is valid
                    is_valid, reason = APIKeyManager.is_key_valid(stored_key)
                    if not is_valid:
                        logger.warning(f"Invalid API key used: {stored_key.key_id} - {reason}")
                        break
                    
                    # Update usage
                    stored_key = APIKeyManager.update_usage(stored_key)
                    await api_key_repo.update(stored_key)
                    
                    # Inject into request state
                    scope["state"] = {
                        "authenticated": True,
                        "api_key_id": stored_key.key_id,
                        "api_key_name": stored_key.name,
                        "scopes": stored_key.scopes,
                        "rate_limit": stored_key.rate_limit_per_minute
                    }
                    
                    authenticated = True
                    logger.info(f"Authenticated request with key: {stored_key.key_id}")
                    break
            
            if not authenticated:
                logger.warning("Invalid API key attempted")
                # Continue without auth (let endpoint handle it)
        
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
        
        # Continue processing
        await self.app(scope, receive, send)


# Dependency injection functions for FastAPI routes

async def get_api_key_repo() -> APIKeyRepository:
    """Get API key repository instance."""
    return APIKeyRepository(db_manager.database)


async def get_current_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    repo: APIKeyRepository = Depends(get_api_key_repo)
) -> Optional[dict]:
    """
    FastAPI dependency to get current authenticated API key.
    
    Returns None if no authentication, raises HTTPException if invalid.
    
    Args:
        api_key: API key from header
        repo: API key repository
        
    Returns:
        Dictionary with API key info or None
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        return None
    
    try:
        # Find and validate key
        active_keys = await repo.find_all_active(limit=1000)
        
        for stored_key in active_keys:
            if APIKeyManager.verify_key(api_key, stored_key.hashed_key):
                # Check validity
                is_valid, reason = APIKeyManager.is_key_valid(stored_key)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"API key is invalid: {reason}",
                        headers={"WWW-Authenticate": "APIKey"}
                    )
                
                # Update usage
                stored_key = APIKeyManager.update_usage(stored_key)
                await repo.update(stored_key)
                
                return {
                    "key_id": stored_key.key_id,
                    "name": stored_key.name,
                    "scopes": stored_key.scopes,
                    "rate_limit": stored_key.rate_limit_per_minute
                }
        
        # Key not found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def require_api_key(
    current_key: Optional[dict] = Depends(get_current_api_key)
) -> dict:
    """
    FastAPI dependency that requires API key authentication.
    
    Use this on endpoints that must be authenticated.
    
    Args:
        current_key: Current API key info (from get_current_api_key)
        
    Returns:
        API key info dictionary
        
    Raises:
        HTTPException: If not authenticated
    """
    if not current_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "APIKey"}
        )
    
    return current_key


async def require_scope(
    required_scope: APIKeyScope
) -> Callable:
    """
    Create a dependency that requires a specific scope.
    
    Usage:
        @app.post("/admin/...")
        async def admin_endpoint(
            key: dict = Depends(require_scope(APIKeyScope.ADMIN))
        ):
            ...
    
    Args:
        required_scope: Required permission scope
        
    Returns:
        FastAPI dependency function
    """
    async def check_permission(current_key: dict = Depends(require_api_key)) -> dict:
        if not check_scope(required_scope, current_key["scopes"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope.value}"
            )
        return current_key
    
    return check_permission


# Convenience dependencies for common scopes
async def require_read(current_key: dict = Depends(require_api_key)) -> dict:
    """Require READ scope."""
    if not check_scope(APIKeyScope.READ, current_key["scopes"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read permission required"
        )
    return current_key


async def require_write(current_key: dict = Depends(require_api_key)) -> dict:
    """Require WRITE scope."""
    if not check_scope(APIKeyScope.WRITE, current_key["scopes"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permission required"
        )
    return current_key


async def require_admin(current_key: dict = Depends(require_api_key)) -> dict:
    """Require ADMIN scope."""
    if not check_scope(APIKeyScope.ADMIN, current_key["scopes"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    return current_key


# Optional authentication (don't fail if no key provided)
async def optional_api_key(
    current_key: Optional[dict] = Depends(get_current_api_key)
) -> Optional[dict]:
    """
    Optional API key authentication.
    
    Returns API key info if provided and valid, None otherwise.
    Does not raise exceptions for missing/invalid keys.
    
    Use this for endpoints that work better with auth but don't require it.
    """
    return current_key

