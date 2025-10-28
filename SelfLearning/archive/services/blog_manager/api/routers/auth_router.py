"""
Authentication and API key management endpoints.

Provides endpoints for creating, managing, and revoking API keys.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ...core.auth import (
    APIKeyManager, APIKey, APIKeyScope, APIKeyStatus
)
from ...core.auth_middleware import (
    require_admin, require_api_key, get_api_key_repo
)
from ...data.api_key_repository import APIKeyRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing API key"},
        403: {"description": "Forbidden - Insufficient permissions"},
        500: {"description": "Internal Server Error"},
    }
)


# Request/Response Models

class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""
    name: str = Field(..., description="Human-readable name for the key", min_length=3)
    scopes: List[APIKeyScope] = Field(
        default=[APIKeyScope.READ],
        description="Permission scopes"
    )
    expires_in_days: Optional[int] = Field(
        None,
        description="Expiration in days (None = never expires)",
        ge=1,
        le=3650  # Max 10 years
    )
    rate_limit_per_minute: int = Field(
        default=100,
        description="Custom rate limit for this key",
        ge=1,
        le=10000
    )
    description: Optional[str] = Field(None, description="Purpose description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production Web App",
                "scopes": ["read", "write"],
                "expires_in_days": 365,
                "rate_limit_per_minute": 1000,
                "description": "Main API key for production web application"
            }
        }


class APIKeyResponse(BaseModel):
    """Response containing API key information."""
    key_id: str
    name: str
    api_key: Optional[str] = Field(None, description="Plain text key (only shown once)")
    scopes: List[APIKeyScope]
    status: APIKeyStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    rate_limit_per_minute: int
    description: Optional[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "key_abc123",
                "name": "Production API Key",
                "api_key": "bmapi_1234567890abcdef...",  # Only on creation
                "scopes": ["read", "write"],
                "status": "active",
                "created_at": "2025-10-13T00:00:00Z",
                "expires_at": "2026-10-13T00:00:00Z",
                "usage_count": 1543,
                "rate_limit_per_minute": 1000
            }
        }


class APIKeyListResponse(BaseModel):
    """Response containing list of API keys."""
    total: int
    keys: List[APIKeyResponse]


class RevokeAPIKeyRequest(BaseModel):
    """Request to revoke an API key."""
    key_id: str = Field(..., description="ID of the key to revoke")


class UsageStatsResponse(BaseModel):
    """API key usage statistics."""
    total: int
    active: int
    revoked: int
    expired: int
    most_used: List[dict]


# Endpoints

@router.post(
    "/keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new API key",
    description="""
    Create a new API key with specified permissions.
    
    **Requires**: ADMIN scope
    
    **Important**: The plain text API key is only returned once.
    Store it securely - it cannot be retrieved later.
    
    **Scopes**:
    - `read`: Read-only access (GET requests)
    - `write`: Read + Write access (POST, PUT, DELETE)
    - `admin`: Full access including key management
    """
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_key: dict = Depends(require_admin),
    repo: APIKeyRepository = Depends(get_api_key_repo)
) -> APIKeyResponse:
    """
    Create a new API key.
    
    Only admins can create API keys.
    """
    try:
        # Generate key
        plain_key, api_key_model = APIKeyManager.create_api_key(
            name=request.name,
            scopes=request.scopes,
            expires_in_days=request.expires_in_days,
            rate_limit_per_minute=request.rate_limit_per_minute,
            description=request.description,
            created_by=current_key["key_id"]
        )
        
        # Store in database
        await repo.create(api_key_model)
        
        # Return with plain key (only time it's shown)
        return APIKeyResponse(
            key_id=api_key_model.key_id,
            name=api_key_model.name,
            api_key=plain_key,  # Only shown once!
            scopes=api_key_model.scopes,
            status=api_key_model.status,
            created_at=api_key_model.created_at,
            expires_at=api_key_model.expires_at,
            last_used_at=api_key_model.last_used_at,
            usage_count=api_key_model.usage_count,
            rate_limit_per_minute=api_key_model.rate_limit_per_minute,
            description=api_key_model.description
        )
    
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get(
    "/keys",
    response_model=APIKeyListResponse,
    summary="List all API keys",
    description="""
    List all API keys (without plain text keys).
    
    **Requires**: ADMIN scope
    """
)
async def list_api_keys(
    current_key: dict = Depends(require_admin),
    repo: APIKeyRepository = Depends(get_api_key_repo),
    limit: int = 100
) -> APIKeyListResponse:
    """List all API keys."""
    try:
        keys = await repo.find_all_active(limit=limit)
        
        key_responses = [
            APIKeyResponse(
                key_id=key.key_id,
                name=key.name,
                api_key=None,  # Never return plain text key
                scopes=key.scopes,
                status=key.status,
                created_at=key.created_at,
                expires_at=key.expires_at,
                last_used_at=key.last_used_at,
                usage_count=key.usage_count,
                rate_limit_per_minute=key.rate_limit_per_minute,
                description=key.description
            )
            for key in keys
        ]
        
        return APIKeyListResponse(
            total=len(key_responses),
            keys=key_responses
        )
    
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.get(
    "/keys/{key_id}",
    response_model=APIKeyResponse,
    summary="Get API key details",
    description="""
    Get details of a specific API key.
    
    **Requires**: ADMIN scope or own key
    """
)
async def get_api_key(
    key_id: str,
    current_key: dict = Depends(require_api_key),
    repo: APIKeyRepository = Depends(get_api_key_repo)
) -> APIKeyResponse:
    """Get API key details."""
    try:
        # Check permissions
        is_admin = APIKeyScope.ADMIN in current_key["scopes"]
        is_own_key = current_key["key_id"] == key_id
        
        if not (is_admin or is_own_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own key or need admin permissions"
            )
        
        # Find key
        key = await repo.find_by_key_id(key_id)
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found"
            )
        
        return APIKeyResponse(
            key_id=key.key_id,
            name=key.name,
            api_key=None,
            scopes=key.scopes,
            status=key.status,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            usage_count=key.usage_count,
            rate_limit_per_minute=key.rate_limit_per_minute,
            description=key.description
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get API key"
        )


@router.delete(
    "/keys/{key_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke API key",
    description="""
    Revoke an API key (soft delete).
    
    **Requires**: ADMIN scope
    
    The key will be marked as revoked and can no longer be used.
    """
)
async def revoke_api_key(
    key_id: str,
    current_key: dict = Depends(require_admin),
    repo: APIKeyRepository = Depends(get_api_key_repo)
) -> dict:
    """Revoke an API key."""
    try:
        # Prevent self-revocation
        if current_key["key_id"] == key_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revoke your own API key"
            )
        
        success = await repo.revoke(key_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found"
            )
        
        return {
            "message": f"API key {key_id} has been revoked",
            "key_id": key_id,
            "status": "revoked"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@router.get(
    "/usage",
    response_model=UsageStatsResponse,
    summary="Get API key usage statistics",
    description="""
    Get usage statistics for all API keys.
    
    **Requires**: ADMIN scope
    """
)
async def get_usage_stats(
    current_key: dict = Depends(require_admin),
    repo: APIKeyRepository = Depends(get_api_key_repo)
) -> UsageStatsResponse:
    """Get API key usage statistics."""
    try:
        stats = await repo.get_usage_stats()
        
        return UsageStatsResponse(**stats)
    
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage statistics"
        )


@router.post(
    "/cleanup",
    status_code=status.HTTP_200_OK,
    summary="Cleanup expired API keys",
    description="""
    Mark expired API keys as EXPIRED status.
    
    **Requires**: ADMIN scope
    """
)
async def cleanup_expired_keys(
    current_key: dict = Depends(require_admin),
    repo: APIKeyRepository = Depends(get_api_key_repo)
) -> dict:
    """Cleanup expired API keys."""
    try:
        count = await repo.cleanup_expired()
        
        return {
            "message": f"Marked {count} expired keys",
            "count": count
        }
    
    except Exception as e:
        logger.error(f"Failed to cleanup expired keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired keys"
        )

