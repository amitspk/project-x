"""
Authentication and authorization for API endpoints.

Provides two types of authentication:
1. Admin authentication - for publisher management endpoints
2. Publisher authentication - for JS library endpoints with domain validation
"""

import logging
from typing import Optional
from urllib.parse import urlparse
from fastapi import Header, HTTPException, Request, Depends

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fyi_widget_api.core.config import get_config
from fyi_widget_shared_library.data.postgres_database import PostgresPublisherRepository
from fyi_widget_shared_library.models.publisher import Publisher

# Import metrics
from fyi_widget_api.api.metrics import publisher_auth_attempts_total

logger = logging.getLogger(__name__)

# Global config instance
config = get_config()

# Global publisher repository (will be set in main.py)
publisher_repo: Optional[PostgresPublisherRepository] = None


def set_publisher_repo(repo: PostgresPublisherRepository):
    """Set the global publisher repository instance."""
    global publisher_repo
    publisher_repo = repo


# ============================================================================
# Admin Authentication
# ============================================================================

async def verify_admin_key(
    request: Request,
    x_admin_key: Optional[str] = Header(None, description="Admin API key for managing publishers")
) -> bool:
    """
    Verify admin API key for publisher management endpoints.
    
    Args:
        x_admin_key: Admin API key from X-Admin-Key header
        
    Returns:
        True if valid
        
    Raises:
        HTTPException: 401 if key is missing or invalid
    """
    if request.method.upper() == "OPTIONS":
        return True
    
    if not x_admin_key:
        logger.warning("Admin endpoint accessed without X-Admin-Key header")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "status_code": 401,
                "message": "Admin authentication required",
                "error": {
                    "code": "UNAUTHORIZED",
                    "detail": "X-Admin-Key header is required for this endpoint"
                }
            }
        )
    
    if not config.admin_api_key:
        logger.error("ADMIN_API_KEY not configured in environment")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "status_code": 500,
                "message": "Admin authentication not configured",
                "error": {
                    "code": "CONFIG_ERROR",
                    "detail": "ADMIN_API_KEY environment variable not set"
                }
            }
        )
    
    if x_admin_key != config.admin_api_key:
        logger.warning(f"Invalid admin key attempt: {x_admin_key[:10]}...")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "status_code": 401,
                "message": "Invalid admin API key",
                "error": {
                    "code": "UNAUTHORIZED",
                    "detail": "The provided admin API key is invalid"
                }
            }
        )
    
    return True


# ============================================================================
# Publisher Authentication
# ============================================================================

def extract_domain(url: str) -> str:
    """
    Extract domain from URL, removing www. prefix.
    
    Args:
        url: Full URL
        
    Returns:
        Domain without www. prefix
    """
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split('/')[0]
    
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return domain.lower()


async def verify_publisher_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, description="Publisher API key for accessing content")
) -> Publisher:
    """
    Verify publisher API key for content endpoints.
    
    This validates:
    1. API key exists and is valid
    2. Publisher account is active
    3. Origin/Referer header matches publisher domain (if present)
    
    Args:
        request: FastAPI request object
        x_api_key: Publisher API key from X-API-Key header
        
    Returns:
        Publisher object if valid
        
    Raises:
        HTTPException: 401/403 if validation fails
    """
    if not x_api_key:
        logger.warning("Publisher endpoint accessed without X-API-Key header")
        publisher_auth_attempts_total.labels(status="invalid_key").inc()
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "status_code": 401,
                "message": "Authentication required",
                "error": {
                    "code": "UNAUTHORIZED",
                    "detail": "X-API-Key header is required"
                }
            }
        )
    
    if not publisher_repo:
        logger.error("Publisher repository not initialized")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "status_code": 500,
                "message": "Authentication service not available",
                "error": {
                    "code": "CONFIG_ERROR",
                    "detail": "Publisher repository not initialized"
                }
            }
        )
    
    # Validate API key
    try:
        publisher = await publisher_repo.get_publisher_by_api_key(x_api_key)
    except Exception as e:
        logger.error(f"Error looking up publisher by API key: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "status_code": 500,
                "message": "Authentication service error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "detail": str(e)
                }
            }
        )
    
    if not publisher:
        logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
        publisher_auth_attempts_total.labels(status="invalid_key").inc()
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "status_code": 401,
                "message": "Invalid API key",
                "error": {
                    "code": "UNAUTHORIZED",
                    "detail": "The provided API key is invalid or has been revoked"
                }
            }
        )
    
    # Check publisher status
    if publisher.status != "active" and publisher.status != "trial":
        logger.warning(f"Inactive publisher attempted access: {publisher.id} (status: {publisher.status})")
        publisher_auth_attempts_total.labels(status="inactive").inc()
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "status_code": 403,
                "message": "Publisher account is not active",
                "error": {
                    "code": "FORBIDDEN",
                    "detail": f"Publisher account status is '{publisher.status}'. Please contact support."
                }
            }
        )
    
    # Validate origin/referer if present (skip in development)
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    
    if origin or referer:
        request_domain = extract_domain(origin or referer)
        publisher_domain = publisher.domain.lower()
        
        # Extract API domain from request (host header) - allow requests from API itself
        api_host = request.headers.get("host", "")
        api_domain = extract_domain(api_host) if api_host else None
        
        # Allow exact match or subdomains of publisher domain
        # Also allow requests from the API domain itself (for Swagger, direct API clients, etc.)
        is_valid_domain = (
            request_domain == publisher_domain or
            request_domain.endswith(f".{publisher_domain}") or
            request_domain == "localhost" or  # Allow localhost for development
            request_domain.startswith("localhost:") or  # Allow localhost with port
            (api_domain and request_domain == api_domain)  # Allow requests from API domain
        )
        
        if not is_valid_domain:
            logger.warning(
                f"Domain mismatch: request from '{request_domain}' but publisher owns '{publisher_domain}'"
            )
            publisher_auth_attempts_total.labels(status="domain_mismatch").inc()
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "status_code": 403,
                    "message": "Domain mismatch",
                    "error": {
                        "code": "FORBIDDEN",
                        "detail": f"Request origin '{request_domain}' does not match publisher domain '{publisher_domain}'"
                    }
                }
            )
    
    # Record successful authentication
    publisher_auth_attempts_total.labels(status="success").inc()
    logger.info(f"Publisher authenticated: {publisher.name} ({publisher.domain})")
    return publisher


async def validate_blog_url_domain(
    blog_url: str,
    publisher: Publisher
) -> None:
    """
    Validate that the blog URL domain matches the publisher's domain.
    
    Args:
        blog_url: The blog URL to process
        publisher: The authenticated publisher
        
    Raises:
        HTTPException: 403 if domains don't match
    """
    blog_domain = extract_domain(blog_url)
    publisher_domain = publisher.domain.lower()
    
    # Allow exact match or subdomains
    is_valid_domain = (
        blog_domain == publisher_domain or
        blog_domain.endswith(f".{publisher_domain}")
    )
    
    if not is_valid_domain:
        logger.warning(
            f"Blog URL domain mismatch: '{blog_domain}' doesn't match publisher domain '{publisher_domain}'"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "status_code": 403,
                "message": "Blog URL domain mismatch",
                "error": {
                    "code": "FORBIDDEN",
                    "detail": f"Blog URL domain '{blog_domain}' does not match your publisher domain '{publisher_domain}'"
                }
            }
        )


# ============================================================================
# Convenience Dependencies
# ============================================================================

async def get_current_publisher(
    publisher: Publisher = Depends(verify_publisher_key)
) -> Publisher:
    """
    Convenience dependency to get the current authenticated publisher.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(publisher: Publisher = Depends(get_current_publisher)):
            # Use publisher object
    """
    return publisher


async def require_admin() -> bool:
    """
    Convenience dependency that requires admin authentication.
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(require_admin)])
        async def endpoint():
            # Admin is authenticated
    """
    return await verify_admin_key()

