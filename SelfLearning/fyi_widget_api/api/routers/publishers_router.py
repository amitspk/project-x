"""
Publisher onboarding and management API.

Endpoints for creating, updating, and managing publishers.
All endpoints require admin authentication via X-Admin-Key header.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Header, Request

# Add shared to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Import auth
from fyi_widget_api.api.auth import verify_admin_key, get_current_publisher, validate_blog_url_domain

from fyi_widget_shared_library.models.publisher import (
    Publisher,
    PublisherCreateRequest,
    PublisherUpdateRequest,
    PublisherResponse,
    PublisherListResponse,
    PublisherStatus
)
from fyi_widget_shared_library.models import (
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
from fyi_widget_shared_library.data.postgres_database import PostgresPublisherRepository
from fyi_widget_shared_library.utils import (
    success_response,
    handle_http_exception,
    handle_generic_exception,
    generate_request_id,
    extract_domain
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Global repository instance (will be initialized in main.py)
publisher_repo: Optional[PostgresPublisherRepository] = None


def get_publisher_repo() -> PostgresPublisherRepository:
    """Dependency to get publisher repository."""
    if publisher_repo is None:
        raise HTTPException(
            status_code=500,
            detail="Publisher repository not initialized"
        )
    return publisher_repo


async def enrich_publisher_with_widget_config(
    publisher: Publisher,
    repo: PostgresPublisherRepository
) -> Dict[str, Any]:
    """
    Enrich publisher response with widget config from database.
    
    The widget config is stored in config.widget in the database JSON,
    but the PublisherConfig Pydantic model doesn't include it.
    This function fetches the raw config and adds widget config to the response.
    """
    # Get raw config from database to access widget config
    raw_config = await repo.get_publisher_raw_config_by_domain(
        publisher.domain,
        allow_subdomain=False
    )
    
    # Convert publisher to dict
    publisher_dict = publisher.model_dump()
    
    # Add widget config if it exists
    if raw_config and isinstance(raw_config, dict):
        widget_config = raw_config.get("widget")
        if widget_config:
            # Ensure config dict exists
            if "config" not in publisher_dict:
                publisher_dict["config"] = {}
            publisher_dict["config"]["widget"] = widget_config
    
    return publisher_dict


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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Onboard a new publisher.
    
    Creates a new publisher account with custom configuration.
    Returns the publisher details including a generated API key.
    
    **Configuration Options:**
    - You can omit the `config` field entirely to use all default values
    - You can pass `config` with only the fields you want to customize
    - All fields not provided will use their default values from the model
    
    Example with custom config:
    ```json
    {
        "name": "Tech Blog Inc",
        "domain": "techblog.com",
        "email": "admin@techblog.com",
        "config": {
            "questions_per_blog": 7,
            "summary_model": "gpt-4o-mini"
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
        
        # Check if domain already exists
        existing = await repo.get_publisher_by_domain(request.domain)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Publisher with domain '{request.domain}' already exists"
            )
        
        # Create publisher object
        publisher = Publisher(
            name=request.name,
            domain=request.domain,
            email=request.email,
            config=request.config,
            subscription_tier=request.subscription_tier
        )
        
        # Save to database
        created_publisher = await repo.create_publisher(publisher)
        
        logger.info(f"[{request_id}] ✅ Publisher onboarded: {created_publisher.id}")
        
        # Enrich with widget config from database (may be empty for new publisher)
        enriched_publisher = await enrich_publisher_with_widget_config(created_publisher, repo)
        
        publisher_response = PublisherResponse(
            success=True,
            publisher=created_publisher,  # Use original for Pydantic validation
            api_key=created_publisher.api_key,  # Only returned on creation
            message="Publisher onboarded successfully"
        )
        
        # Get the response dict and update it with enriched data
        response_dict = publisher_response.model_dump()
        response_dict["publisher"] = enriched_publisher
        
        return success_response(
            result=response_dict,
            message="Publisher onboarded successfully",
            status_code=201,
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
    adVariation: str = Query(..., description="Ad variation to return: 'adsenseForSearch', 'adsenseDisplay', or 'googleAdManager'"),
    publisher: Publisher = Depends(get_current_publisher),
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Get publisher metadata including widget configuration and ad settings.
    
    **Authentication**: Requires X-API-Key header with valid publisher API key.
    
    **Parameters**:
    - `blog_url`: Full blog URL (e.g., https://example.com/blog/post)
    - `adVariation`: Which ad configuration to return ('adsenseForSearch', 'adsenseDisplay', or 'googleAdManager')
    
    **Response**:
    Returns publisher metadata including:
    - Domain, publisher ID, and name
    - Widget configuration (theme, GA settings, etc.)
    - Ad configuration for the requested variation (others will be null)
    
    The widget config is stored in the `config.widget` JSON column in the database.
    """
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        # Validate adVariation parameter
        valid_ad_variations = ["adsenseForSearch", "adsenseDisplay", "googleAdManager"]
        if adVariation not in valid_ad_variations:
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "status_code": 422,
                    "message": "Validation error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "detail": f"adVariation must be one of: {', '.join(valid_ad_variations)}"
                    }
                }
            )
        
        # Extract domain from blog_url
        blog_domain = extract_domain(blog_url)
        logger.info(f"[{request_id}] 📖 Getting publisher metadata for domain: {blog_domain} (adVariation: {adVariation})")
        
        # Validate blog URL domain matches publisher's domain
        await validate_blog_url_domain(blog_url, publisher)
        
        # Get publisher by domain (with subdomain support) to ensure we have the latest config
        # This also handles subdomain matching (e.g., info.contentretina.com -> contentretina.com)
        domain_publisher = await repo.get_publisher_by_domain(blog_domain, allow_subdomain=True)
        
        if not domain_publisher:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "status_code": 404,
                    "message": "Publisher not found for the provided blog URL",
                    "error": {
                        "code": "NOT_FOUND",
                        "detail": f"No publisher found for domain: {blog_domain}"
                    }
                }
            )
        
        # Get raw config JSON from database to access nested widget config
        # The PublisherConfig Pydantic model doesn't include widget config, so we need raw JSON
        raw_config = await repo.get_publisher_raw_config_by_domain(blog_domain, allow_subdomain=True)
        
        if not raw_config:
            raw_config = {}
        
        # Extract widget config from config.widget (nested structure)
        widget_config = raw_config.get("widget", {}) if isinstance(raw_config, dict) else {}
        
        # Build result with widget config fields (return null if missing)
        result_data = {
            "domain": domain_publisher.domain,
            "publisher_id": domain_publisher.id,
            "publisher_name": domain_publisher.name,
            "useDummyData": widget_config.get("useDummyData"),
            "theme": widget_config.get("theme"),
            "currentStructure": widget_config.get("currentStructure"),
            "gaTrackingId": widget_config.get("gaTrackingId"),
            "gaEnabled": widget_config.get("gaEnabled"),
            "adsenseForSearch": None,
            "adsenseDisplay": None,
            "googleAdManager": None
        }
        
        # Set the requested ad variation config, others remain null
        if adVariation == "adsenseForSearch":
            adsense_for_search = widget_config.get("adsenseForSearch")
            if adsense_for_search:
                result_data["adsenseForSearch"] = adsense_for_search
        elif adVariation == "adsenseDisplay":
            adsense_display = widget_config.get("adsenseDisplay")
            if adsense_display:
                result_data["adsenseDisplay"] = adsense_display
        elif adVariation == "googleAdManager":
            google_ad_manager = widget_config.get("googleAdManager")
            if google_ad_manager:
                result_data["googleAdManager"] = google_ad_manager
        
        logger.info(f"[{request_id}] ✅ Publisher metadata retrieved for: {domain_publisher.domain}")
        
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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """Get publisher by ID."""
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📖 Getting publisher: {publisher_id}")
        
        publisher = await repo.get_publisher_by_id(publisher_id)
        
        if not publisher:
            raise HTTPException(
                status_code=404,
                detail=f"Publisher not found: {publisher_id}"
            )
        
        # Don't return API key in GET requests
        publisher.api_key = None
        
        # Enrich with widget config from database
        enriched_publisher = await enrich_publisher_with_widget_config(publisher, repo)
        
        # Create response with enriched publisher dict (widget config included)
        publisher_response = PublisherResponse(
            success=True,
            publisher=publisher  # Use original publisher for Pydantic validation
        )
        
        # Get the response dict and update it with enriched data
        response_dict = publisher_response.model_dump()
        response_dict["publisher"] = enriched_publisher
        
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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
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
        
        # Enable subdomain matching for admin lookups (e.g., info.contentretina.com -> contentretina.com)
        publisher = await repo.get_publisher_by_domain(domain, allow_subdomain=True)
        
        if not publisher:
            raise HTTPException(
                status_code=404,
                detail=f"Publisher not found for domain: {domain}"
            )
        
        # Don't return API key
        publisher.api_key = None
        
        # Enrich with widget config from database
        enriched_publisher = await enrich_publisher_with_widget_config(publisher, repo)
        
        # Create response with enriched publisher dict (widget config included)
        publisher_response = PublisherResponse(
            success=True,
            publisher=publisher  # Use original publisher for Pydantic validation
        )
        
        # Get the response dict and update it with enriched data
        response_dict = publisher_response.model_dump()
        response_dict["publisher"] = enriched_publisher
        
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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Update publisher configuration.
    
    **Admin Only**: This endpoint requires admin authentication (X-Admin-Key header).
    
    Allows updating publisher name, email, status, configuration, and subscription tier.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📝 Updating publisher: {publisher_id}")
        
        # Build updates dict (only include non-None values)
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.email is not None:
            updates['email'] = request.email
        if request.status is not None:
            updates['status'] = request.status
        if request.config is not None:
            updates['config'] = request.config
        if request.subscription_tier is not None:
            updates['subscription_tier'] = request.subscription_tier
        
        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No fields to update"
            )
        
        # Update publisher
        updated_publisher = await repo.update_publisher(publisher_id, updates)
        
        if not updated_publisher:
            raise HTTPException(
                status_code=404,
                detail=f"Publisher not found: {publisher_id}"
            )
        
        # Don't return API key
        updated_publisher.api_key = None
        
        logger.info(f"[{request_id}] ✅ Publisher updated: {publisher_id}")
        
        # Enrich with widget config from database
        enriched_publisher = await enrich_publisher_with_widget_config(updated_publisher, repo)
        
        publisher_response = PublisherResponse(
            success=True,
            publisher=updated_publisher,  # Use original for Pydantic validation
            message="Publisher updated successfully"
        )
        
        # Get the response dict and update it with enriched data
        response_dict = publisher_response.model_dump()
        response_dict["publisher"] = enriched_publisher
        
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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
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
        
        # Check if publisher exists
        publisher = await repo.get_publisher_by_id(publisher_id)
        if not publisher:
            raise HTTPException(
                status_code=404,
                detail=f"Publisher not found: {publisher_id}"
            )
        
        # Soft delete - mark as inactive
        await repo.update_publisher(publisher_id, {"status": PublisherStatus.INACTIVE})
        
        logger.info(f"[{request_id}] ✅ Publisher deleted: {publisher_id}")
        
        result_data = {
            "success": True,
            "message": "Publisher deleted successfully"
        }
        
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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
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
        
        # Check if publisher exists
        publisher = await repo.get_publisher_by_id(publisher_id)
        if not publisher:
            raise HTTPException(
                status_code=404,
                detail=f"Publisher not found: {publisher_id}"
            )
        
        # Check if already active
        if publisher.status == PublisherStatus.ACTIVE:
            logger.warning(f"[{request_id}] ⚠️ Publisher already active: {publisher_id}")
            raise HTTPException(
                status_code=400,
                detail="Publisher is already active"
            )
        
        # Reactivate - mark as active
        await repo.update_publisher(publisher_id, {"status": PublisherStatus.ACTIVE})
        
        # Get updated publisher
        updated_publisher = await repo.get_publisher_by_id(publisher_id)
        updated_publisher.api_key = None  # Don't return API key
        
        logger.info(f"[{request_id}] ✅ Publisher reactivated: {publisher_id}")
        
        # Enrich with widget config from database
        enriched_publisher = await enrich_publisher_with_widget_config(updated_publisher, repo)
        
        publisher_response = PublisherResponse(
            success=True,
            publisher=updated_publisher,  # Use original for Pydantic validation
            message="Publisher reactivated successfully"
        )
        
        # Get the response dict and update it with enriched data
        response_dict = publisher_response.model_dump()
        response_dict["publisher"] = enriched_publisher
        
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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    List all publishers with pagination.
    
    Can filter by status (active, inactive, suspended, trial).
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📋 Listing publishers (status={status}, page={page})")
        
        publishers, total = await repo.list_publishers(status, page, page_size)
        
        # Don't return API keys
        for pub in publishers:
            pub.api_key = None
        
        # Create list response first (for Pydantic validation)
        list_response = PublisherListResponse(
            success=True,
            publishers=publishers,
            total=total,
            page=page,
            page_size=page_size
        )
        
        # Enrich each publisher with widget config
        response_dict = list_response.model_dump()
        enriched_publishers = []
        for pub in publishers:
            enriched = await enrich_publisher_with_widget_config(pub, repo)
            enriched_publishers.append(enriched)
        response_dict["publishers"] = enriched_publishers
        
        return success_response(
            result=response_dict,
            message=f"Retrieved {len(enriched_publishers)} publishers",
            status_code=200,
            metadata={"total": total, "page": page, "page_size": page_size},
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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
) -> Dict[str, Any]:
    """
    Get publisher configuration.
    
    Returns only the config object, useful for workers/services.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] ⚙️ Getting config for publisher: {publisher_id}")
        
        publisher = await repo.get_publisher_by_id(publisher_id)
        
        if not publisher:
            raise HTTPException(
                status_code=404,
                detail=f"Publisher not found: {publisher_id}"
            )
        
        # Get raw config from database to include widget config
        raw_config = await repo.get_publisher_raw_config_by_domain(
            publisher.domain,
            allow_subdomain=False
        )
        
        # Start with the Pydantic model config
        config_dict = publisher.config.model_dump()
        
        # Add widget config if it exists in raw config
        if raw_config and isinstance(raw_config, dict):
            widget_config = raw_config.get("widget")
            if widget_config:
                config_dict["widget"] = widget_config
        
        config_data = {
            "success": True,
            "config": config_dict
        }
        
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
    repo: PostgresPublisherRepository = Depends(get_publisher_repo)
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
        
        # Regenerate API key
        publisher, new_api_key = await repo.regenerate_api_key(publisher_id)
        
        logger.info(f"[{request_id}] ✅ API key regenerated for: {publisher.name}")
        
        # Create response
        response_data = success_response(
            message="API key regenerated successfully",
            result={
                "publisher": {
                    "id": publisher.id,
                    "name": publisher.name,
                    "domain": publisher.domain,
                    "email": publisher.email,
                    "status": publisher.status,
                    "config": {
                        "questions_per_blog": publisher.config.questions_per_blog,
                        "summary_model": publisher.config.summary_model.value if hasattr(publisher.config.summary_model, 'value') else str(publisher.config.summary_model),
                        "questions_model": publisher.config.questions_model.value if hasattr(publisher.config.questions_model, 'value') else str(publisher.config.questions_model),
                        "chat_model": publisher.config.chat_model.value if hasattr(publisher.config.chat_model, 'value') else str(publisher.config.chat_model),
                        "summary_temperature": publisher.config.summary_temperature,
                        "questions_temperature": publisher.config.questions_temperature,
                        "chat_temperature": publisher.config.chat_temperature,
                        "summary_max_tokens": publisher.config.summary_max_tokens,
                        "questions_max_tokens": publisher.config.questions_max_tokens,
                        "chat_max_tokens": publisher.config.chat_max_tokens,
                        "generate_summary": publisher.config.generate_summary,
                        "generate_embeddings": publisher.config.generate_embeddings,
                        "use_grounding": publisher.config.use_grounding,
                        "daily_blog_limit": publisher.config.daily_blog_limit
                    },
                    "created_at": publisher.created_at.isoformat() if publisher.created_at else None,
                    "subscription_tier": publisher.subscription_tier
                },
                "api_key": new_api_key,
                "message": "⚠️ IMPORTANT: Save this API key now - it won't be shown again! The old key has been invalidated."
            },
            status_code=200,
            request_id=request_id
        )
        
        return response_data
        
    except ValueError as e:
        logger.warning(f"[{request_id}] ⚠️ Publisher not found: {publisher_id}")
        response_data = handle_http_exception(
            status_code=404,
            message=str(e),
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
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
