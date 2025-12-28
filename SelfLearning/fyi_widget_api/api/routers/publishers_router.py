"""
Publisher onboarding and management API.

Endpoints for creating, updating, and managing publishers.
All endpoints require admin authentication via X-Admin-Key header.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request

# Import auth/deps
from fyi_widget_api.api.auth import verify_admin_key, get_current_publisher
from fyi_widget_api.api.deps import get_publisher_repo
from fyi_widget_api.api.services.publisher_service import PublisherService

from fyi_widget_api.api.models.publisher_models import (
    Publisher,
    PublisherCreateRequest,
    PublisherUpdateRequest,
    PublisherStatus
)
from fyi_widget_api.api.models import (
    PublisherOnboardResponse,
    PublisherGetResponse,
    PublishersListResponse as SwaggerPublishersListResponse,
    PublisherUpdateResponse as SwaggerPublisherUpdateResponse,
    PublisherDeleteResponse,
    PublisherConfigResponse,
    PublisherRegenerateApiKeyResponse,
    PublisherMetadataResponse,
    StandardErrorResponse
)
from fyi_widget_api.api.repositories import PublisherRepository
from fyi_widget_api.api.utils import (
    success_response,
    handle_http_exception,
    handle_generic_exception,
    generate_request_id
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/onboard",
    status_code=201,
    response_model=PublisherOnboardResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        201: {"description": "Publisher onboarded successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        409: {"model": StandardErrorResponse, "description": "Publisher with domain already exists"}
    }
)
async def onboard_publisher(
    http_request: Request,
    request: PublisherCreateRequest,
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Onboard a new publisher.
    
    Creates a new publisher account with custom configuration.
    Returns the publisher details including a generated API key.
    
    **Configuration Options:**
    - You can omit the `config` field entirely to use all default values
    - You can pass `config` with only the fields you want to customize
    - All fields not provided will use their default values from the model
    - `widget_config` is required and must be provided to set widget-specific settings (theme, GA, ads, etc.)
    
    Example with custom config and widget_config:
    ```json
    {
        "name": "Tech Blog Inc",
        "domain": "techblog.com",
        "email": "admin@techblog.com",
        "config": {
            "questions_per_blog": 7,
            "summary_model": "gpt-4o-mini"
        },
        "widget_config": {
            "theme": "light",
            "gaTrackingId": "G-XXXXXXXXXX",
            "gaEnabled": true,
            "adsenseForSearch": {
                "enabled": true,
                "pubId": "partner-pub-XXXXX"
            }
        }
    }
    ```
    
    Example using defaults (config omitted):
    ```json
    {
        "name": "Tech Blog Inc",
        "domain": "techblog.com",
        "email": "admin@techblog.com"
    }
    ```
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📝 Onboarding publisher: {request.name} ({request.domain})")
        
        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        response_dict, status_code, message = await publisher_service.onboard_publisher(
            request=request,
            request_id=request_id,
        )

        return success_response(
            result=response_dict,
            message=message,
            status_code=status_code,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Publisher onboarding failed: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to onboard publisher",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/metadata",
    response_model=PublisherMetadataResponse,
    responses={
        200: {"description": "Publisher metadata retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Authentication required - X-API-Key header missing"},
        403: {"model": StandardErrorResponse, "description": "Publisher account not active or domain mismatch"},
        404: {"model": StandardErrorResponse, "description": "Publisher not found for the provided blog URL"},
        422: {"model": StandardErrorResponse, "description": "Validation error - missing or invalid parameters"}
    }
)
async def get_publisher_metadata(
    http_request: Request,
    blog_url: str = Query(..., description="The full blog URL (e.g., https://example.com/blog/post)"),
    publisher: Publisher = Depends(get_current_publisher),
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Get publisher metadata including widget configuration and ad settings.
    
    **Authentication**: Requires X-API-Key header with valid publisher API key.
    
    **Parameters**:
    - `blog_url`: Full blog URL (e.g., https://example.com/blog/post)
    
    **Response**:
    Returns publisher metadata including:
    - Domain, publisher ID, and name
    - Widget configuration (theme, GA settings, etc.)
    - Ad configuration based on `adVariation` stored in widget config (others will be null)
    
    The `adVariation` field in widget config determines which ad configuration to return.
    Valid values: 'adsenseForSearch', 'adsenseDisplay', or 'googleAdManager'
    
    The widget config is stored in the `config.widget` JSON column in the database.
    """
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        result_data = await publisher_service.get_publisher_metadata(
            blog_url=blog_url,
            publisher=publisher,
            request_id=request_id,
        )

        return success_response(
            result=result_data,
            message="Publisher metadata retrieved successfully",
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        # Re-raise HTTPException as-is (it already has proper format)
        raise
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to get publisher metadata: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to get publisher metadata",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/{publisher_id}",
    response_model=PublisherGetResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Publisher retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Publisher not found"}
    }
)
async def get_publisher(
    http_request: Request,
    publisher_id: str,
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """Get publisher by ID."""
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📖 Getting publisher: {publisher_id}")
        
        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        response_dict = await publisher_service.get_publisher(
            publisher_id=publisher_id,
        )

        return success_response(
            result=response_dict,
            message="Publisher retrieved successfully",
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to get publisher: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to get publisher",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/by-domain/{domain}",
    response_model=PublisherGetResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Publisher retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Publisher not found for domain"}
    }
)
async def get_publisher_by_domain(
    http_request: Request,
    domain: str,
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Get publisher by domain.
    
    Useful for checking if a domain is already onboarded.
    Supports subdomain matching (e.g., info.contentretina.com will find contentretina.com publisher).
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📖 Getting publisher by domain: {domain}")
        
        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        response_dict = await publisher_service.get_publisher_by_domain(
            domain=domain,
        )

        return success_response(
            result=response_dict,
            message="Publisher retrieved successfully",
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to get publisher by domain: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to get publisher by domain",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.put(
    "/{publisher_id}",
    response_model=SwaggerPublisherUpdateResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Publisher updated successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Publisher not found"}
    }
)
async def update_publisher(
    http_request: Request,
    publisher_id: str,
    request: PublisherUpdateRequest,
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Update publisher configuration.
    
    **Admin Only**: This endpoint requires admin authentication (X-Admin-Key header).
    
    Allows updating publisher name, email, status, configuration, and subscription tier.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    # Extract widget from raw request body if it's nested in config (Pydantic strips it)
    widget_from_request = None
    if hasattr(http_request.state, 'raw_body'):
        try:
            import json
            raw_body_str = http_request.state.raw_body
            logger.info(f"[{request_id}] 📦 Raw body length: {len(raw_body_str) if raw_body_str else 0} bytes")
            body = json.loads(raw_body_str)
            logger.info(f"[{request_id}] 📦 Parsed body keys: {list(body.keys()) if isinstance(body, dict) else 'N/A'}")
            
            # Check for widget_config as top-level key
            if isinstance(body, dict) and "widget_config" in body:
                widget_from_request = body.get("widget_config")
                logger.info(f"[{request_id}] 🔍 Found widget_config in raw body (top-level) with keys: {list(widget_from_request.keys()) if isinstance(widget_from_request, dict) else 'N/A'}")
            # Check for widget as top-level key (alternative format)
            elif isinstance(body, dict) and "widget" in body:
                widget_from_request = body.get("widget")
                logger.info(f"[{request_id}] 🔍 Found widget in raw body (top-level) with keys: {list(widget_from_request.keys()) if isinstance(widget_from_request, dict) else 'N/A'}")
            # Check for widget nested in config
            elif isinstance(body, dict) and "config" in body and isinstance(body["config"], dict) and "widget" in body["config"]:
                widget_from_request = body["config"].get("widget")
                logger.info(f"[{request_id}] 🔍 Found widget in raw body (nested in config) with keys: {list(widget_from_request.keys()) if isinstance(widget_from_request, dict) else 'N/A'}")
            else:
                logger.info(f"[{request_id}] ⚠️ Widget not found in raw body. Body structure: widget={('widget' in body) if isinstance(body, dict) else False}, config={('config' in body) if isinstance(body, dict) else False}, widget_config={('widget_config' in body) if isinstance(body, dict) else False}")
        except Exception as e:
            logger.warning(f"[{request_id}] ⚠️ Failed to parse raw body: {e}", exc_info=True)
    else:
        logger.warning(f"[{request_id}] ⚠️ No raw_body in request.state")
    
    try:
        logger.info(f"[{request_id}] 📝 Updating publisher: {publisher_id}")
        logger.info(
            f"[{request_id}] 🔍 Request check - config: {request.config is not None}, widget_config: {request.widget_config is not None}, widget_from_request: {widget_from_request is not None}"
        )

        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        response_dict = await publisher_service.update_publisher(
            publisher_id=publisher_id,
            request=request,
            request_id=request_id,
        )

        return success_response(
            result=response_dict,
            message="Publisher updated successfully",
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to update publisher: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to update publisher",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.delete(
    "/{publisher_id}",
    response_model=PublisherDeleteResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Publisher deleted successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Publisher not found"}
    }
)
async def delete_publisher(
    http_request: Request,
    publisher_id: str,
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Delete a publisher.
    
    **Admin Only**: This endpoint requires admin authentication (X-Admin-Key header).
    
    This is a soft delete - the publisher is marked as inactive.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 🗑️ Deleting publisher: {publisher_id}")
        
        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        result_data = await publisher_service.delete_publisher(
            publisher_id=publisher_id,
        )
        
        return success_response(
            result=result_data,
            message="Publisher deleted successfully",
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to delete publisher: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to delete publisher",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.post(
    "/{publisher_id}/reactivate",
    response_model=SwaggerPublisherUpdateResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Publisher reactivated successfully"},
        400: {"model": StandardErrorResponse, "description": "Publisher is already active"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Publisher not found"}
    }
)
async def reactivate_publisher(
    http_request: Request,
    publisher_id: str,
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Reactivate a deleted/inactive publisher.
    
    **Admin Only**: This endpoint requires admin authentication (X-Admin-Key header).
    
    Marks the publisher as ACTIVE again. Useful when you've soft-deleted a publisher
    and want to restore it instead of creating a new one.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 🔄 Reactivating publisher: {publisher_id}")
        
        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        response_dict = await publisher_service.reactivate_publisher(
            publisher_id=publisher_id,
            request_id=request_id,
        )

        return success_response(
            result=response_dict,
            message="Publisher reactivated successfully",
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to reactivate publisher: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to reactivate publisher",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/",
    response_model=SwaggerPublishersListResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Publishers retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"}
    }
)
async def list_publishers(
    http_request: Request,
    status: Optional[PublisherStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    List all publishers with pagination.
    
    Can filter by status (active, inactive, suspended, trial).
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📋 Listing publishers (status={status}, page={page})")
        
        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        response_dict = await publisher_service.list_publishers(
            status=status,
            page=page,
            page_size=page_size,
        )
        
        return success_response(
            result=response_dict,
            message=f"Retrieved {len(response_dict.get('publishers', []))} publishers",
            status_code=200,
            metadata={
                "total": response_dict.get("total"),
                "page": page,
                "page_size": page_size,
            },
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to list publishers: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to list publishers",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/{publisher_id}/config",
    response_model=PublisherConfigResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Publisher configuration retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Publisher not found"}
    }
)
async def get_publisher_config(
    http_request: Request,
    publisher_id: str,
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Get publisher configuration.
    
    Returns only the config object, useful for workers/services.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] ⚙️ Getting config for publisher: {publisher_id}")
        
        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        config_data = await publisher_service.get_publisher_config(
            publisher_id=publisher_id,
        )
        
        return success_response(
            result=config_data,
            message="Publisher configuration retrieved successfully",
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to get config: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to get publisher configuration",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )

@router.post(
    "/{publisher_id}/regenerate-api-key",
    status_code=200,
    response_model=PublisherRegenerateApiKeyResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "API key regenerated successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Publisher not found"}
    }
)
async def regenerate_publisher_api_key(
    http_request: Request,
    publisher_id: str,
    repo: PublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Regenerate API key for a publisher.
    
    **Admin Only**: This endpoint requires admin authentication.
    
    This will:
    1. Generate a new API key for the publisher
    2. Invalidate the old API key immediately
    3. Return the new API key (save it - won't be shown again!)
    
    **Use cases**:
    - Publisher lost their API key
    - API key was compromised
    - Security audit requires key rotation
    
    **⚠️ Warning**: The old API key will stop working immediately!
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 🔄 Regenerating API key for publisher: {publisher_id}")

        # Instantiate service with injected dependencies
        publisher_service = PublisherService(publisher_repo=repo)
        
        response_data = await publisher_service.regenerate_api_key(
            publisher_id=publisher_id,
            request_id=request_id,
        )

        return response_data

    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to regenerate API key: {e}", exc_info=True)
        response_data = handle_generic_exception(
            error=e,
            message="Failed to regenerate API key",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
