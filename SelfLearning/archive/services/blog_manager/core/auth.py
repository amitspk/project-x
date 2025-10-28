"""
Authentication and authorization for the Blog Manager API.

Implements API key-based authentication with secure key storage and management.
"""

import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from passlib.hash import bcrypt
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class APIKeyScope(str, Enum):
    """API key permission scopes."""
    READ = "read"  # Read-only access (GET requests)
    WRITE = "write"  # Write access (POST, PUT, DELETE)
    ADMIN = "admin"  # Full access including key management


class APIKeyStatus(str, Enum):
    """API key status."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class APIKey(BaseModel):
    """API Key model for database storage."""
    
    key_id: str = Field(..., description="Unique identifier for the key")
    name: str = Field(..., description="Human-readable name for the key")
    hashed_key: str = Field(..., description="Bcrypt-hashed API key")
    scopes: List[APIKeyScope] = Field(default=[APIKeyScope.READ], description="Permission scopes")
    status: APIKeyStatus = Field(default=APIKeyStatus.ACTIVE, description="Key status")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Expiration date (optional)")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    
    # Usage tracking
    usage_count: int = Field(default=0, description="Number of times key was used")
    rate_limit_per_minute: int = Field(default=100, description="Custom rate limit for this key")
    
    # Audit
    created_by: Optional[str] = Field(None, description="Who created this key")
    description: Optional[str] = Field(None, description="Key purpose description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "key_abc123",
                "name": "Production API Key",
                "scopes": ["read", "write"],
                "rate_limit_per_minute": 1000,
                "description": "Main production key for web app"
            }
        }


class APIKeyManager:
    """
    Manages API key generation, validation, and lifecycle.
    
    Features:
    - Secure key generation (cryptographically random)
    - Bcrypt hashing for storage
    - Key validation and verification
    - Usage tracking
    - Expiration handling
    """
    
    KEY_PREFIX = "bmapi_"  # Blog Manager API
    KEY_LENGTH = 32  # 32 random bytes = 64 hex chars
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a secure API key.
        
        Format: bmapi_{64_hex_chars}
        
        Returns:
            Cryptographically secure API key
        """
        random_bytes = secrets.token_hex(APIKeyManager.KEY_LENGTH)
        return f"{APIKeyManager.KEY_PREFIX}{random_bytes}"
    
    @staticmethod
    def hash_key(api_key: str) -> str:
        """
        Hash an API key for secure storage.
        
        Uses bcrypt with default cost factor (12 rounds).
        
        Args:
            api_key: Plain text API key
            
        Returns:
            Bcrypt hash of the key
        """
        return bcrypt.hash(api_key)
    
    @staticmethod
    def verify_key(api_key: str, hashed_key: str) -> bool:
        """
        Verify an API key against its hash.
        
        Args:
            api_key: Plain text API key from request
            hashed_key: Stored bcrypt hash
            
        Returns:
            True if key matches, False otherwise
        """
        try:
            return bcrypt.verify(api_key, hashed_key)
        except Exception as e:
            logger.error(f"Key verification error: {e}")
            return False
    
    @staticmethod
    def create_api_key(
        name: str,
        scopes: List[APIKeyScope] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_per_minute: int = 100,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> tuple[str, APIKey]:
        """
        Create a new API key with metadata.
        
        Args:
            name: Human-readable name for the key
            scopes: Permission scopes (default: READ only)
            expires_in_days: Expiration in days (None = never expires)
            rate_limit_per_minute: Custom rate limit for this key
            description: Purpose description
            created_by: Creator identifier
            
        Returns:
            Tuple of (plain_api_key, api_key_model)
            
        Note:
            The plain API key is only returned once. It must be stored
            by the client and cannot be retrieved later.
        """
        # Generate secure key
        plain_key = APIKeyManager.generate_key()
        hashed_key = APIKeyManager.hash_key(plain_key)
        
        # Generate unique key ID
        key_id = f"key_{secrets.token_hex(8)}"
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Default scopes
        if scopes is None:
            scopes = [APIKeyScope.READ]
        
        # Create model
        api_key_model = APIKey(
            key_id=key_id,
            name=name,
            hashed_key=hashed_key,
            scopes=scopes,
            status=APIKeyStatus.ACTIVE,
            expires_at=expires_at,
            rate_limit_per_minute=rate_limit_per_minute,
            description=description,
            created_by=created_by
        )
        
        logger.info(f"Created new API key: {key_id} ({name})")
        
        return plain_key, api_key_model
    
    @staticmethod
    def is_key_valid(api_key_model: APIKey) -> tuple[bool, Optional[str]]:
        """
        Check if an API key is valid for use.
        
        Args:
            api_key_model: API key model from database
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Check status
        if api_key_model.status == APIKeyStatus.REVOKED:
            return False, "Key has been revoked"
        
        # Check expiration
        if api_key_model.expires_at:
            if datetime.utcnow() > api_key_model.expires_at:
                return False, "Key has expired"
        
        return True, None
    
    @staticmethod
    def update_usage(api_key_model: APIKey) -> APIKey:
        """
        Update key usage statistics.
        
        Args:
            api_key_model: API key model
            
        Returns:
            Updated API key model
        """
        api_key_model.usage_count += 1
        api_key_model.last_used_at = datetime.utcnow()
        return api_key_model


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when user doesn't have required permissions."""
    pass


def check_scope(required_scope: APIKeyScope, user_scopes: List[APIKeyScope]) -> bool:
    """
    Check if user has required scope.
    
    Scope hierarchy:
    - ADMIN has all permissions
    - WRITE includes READ
    - READ is basic access
    
    Args:
        required_scope: Required permission
        user_scopes: User's scopes
        
    Returns:
        True if authorized, False otherwise
    """
    # Admin has everything
    if APIKeyScope.ADMIN in user_scopes:
        return True
    
    # Direct match
    if required_scope in user_scopes:
        return True
    
    # WRITE includes READ
    if required_scope == APIKeyScope.READ and APIKeyScope.WRITE in user_scopes:
        return True
    
    return False


# Dependency injection helpers for FastAPI
class APIKeyHeader:
    """Extract API key from request header."""
    
    def __init__(self, header_name: str = "X-API-Key"):
        self.header_name = header_name
    
    def __call__(self, request) -> Optional[str]:
        """Extract API key from request headers."""
        return request.headers.get(self.header_name)


def get_api_key_from_header(
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    FastAPI dependency to extract API key from header.
    
    Args:
        api_key: API key from X-API-Key header
        
    Returns:
        API key string or None
    """
    return api_key

