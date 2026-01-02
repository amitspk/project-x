"""V2 Questions router - uses new blog_processing_queue architecture."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request, Depends, Security

from fyi_widget_api.api.models import CheckAndLoadResponse, StandardErrorResponse
from fyi_widget_api.api.models.publisher_models import Publisher
from fyi_widget_api.api.repositories import QuestionRepository, PublisherRepository
from fyi_widget_api.api.repositories.blog_processing_queue_repository import BlogProcessingQueueRepository
from fyi_widget_api.api.repositories.blog_metadata_repository import BlogMetadataRepository
from fyi_widget_api.api.services.blog_processing_service import BlogProcessingService
from fyi_widget_api.api.utils import (
    normalize_url,
    success_response,
    handle_http_exception,
    handle_generic_exception,
    generate_request_id
)
from fyi_widget_api.api.auth import get_current_publisher, publisher_key_header
from fyi_widget_api.api.services.auth_service import validate_blog_url_domain

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency injection for v2 repositories
def get_blog_queue_repository(request: Request) -> BlogProcessingQueueRepository:
    """Get blog processing queue repository from app state."""
    db = request.app.state.mongodb_database
    return BlogProcessingQueueRepository(database=db)


def get_question_repository_v2(request: Request) -> QuestionRepository:
    """Get question repository from app state."""
    db = request.app.state.mongodb_database
    return QuestionRepository(database=db)


def get_publisher_repository_v2(request: Request) -> PublisherRepository:
    """Get publisher repository from app state."""
    # Return the already-connected instance from app state
    return request.app.state.publisher_repo


def get_blog_metadata_repository_v2(request: Request) -> BlogMetadataRepository:
    """Get blog metadata repository from app state."""
    db = request.app.state.mongodb_database
    return BlogMetadataRepository(database=db)


# Dependency injection for v2 service
def get_blog_processing_service(
    queue_repo: BlogProcessingQueueRepository = Depends(get_blog_queue_repository),
    question_repo: QuestionRepository = Depends(get_question_repository_v2),
    publisher_repo: PublisherRepository = Depends(get_publisher_repository_v2),
    metadata_repo: BlogMetadataRepository = Depends(get_blog_metadata_repository_v2),
) -> BlogProcessingService:
    """
    Get BlogProcessingService with all dependencies injected.
    
    This follows proper DI pattern - the service is created with its dependencies,
    not manually instantiated in the endpoint.
    """
    return BlogProcessingService(
        queue_repo=queue_repo,
        question_repo=question_repo,
        publisher_repo=publisher_repo,
        metadata_repo=metadata_repo,
    )


@router.get(
    "/check-and-load",
    response_model=CheckAndLoadResponse,
    responses={
        200: {"description": "Questions ready or processing initiated"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Publisher account not active or domain mismatch"}
    },
    dependencies=[Security(publisher_key_header)]
)
async def check_and_load_questions_v2(
    request: Request,
    blog_url: str = Query(..., description="The blog URL to check and load questions for"),
    publisher: Publisher = Depends(get_current_publisher),
    blog_processing_service: BlogProcessingService = Depends(get_blog_processing_service),
) -> Dict[str, Any]:
    """
    **V2 - New Architecture** Smart question loading endpoint.
    
    **Changes from v1:**
    - Uses `blog_processing_queue` for state management (one entry per blog)
    - Worker polls from `blog_processing_queue` instead of `processing_jobs`
    - Supports automatic reprocessing on failure
    - No more complex job history queries
    
    **Authentication**: Requires X-API-Key header with valid publisher API key.
    
    **Smart Loading Strategy**:
    1. First checks if questions already exist (fast path ⚡)
    2. If YES → Returns questions immediately
    3. If NO → Checks `blog_processing_queue` for current state
    4. Creates entry + reserves slot if new blog
    5. Returns current status if already queued/processing
    6. Auto-requeues if previously failed
    
    **Response States**:
    - `ready`: Questions are available and returned
    - `queued`: Job is queued for processing
    - `processing`: Job is currently processing
    - `retry`: Job is queued for retry after failure
    - `failed`: Processing failed (will auto-requeue on next call)
    
    **Benefits over v1**:
    - Simpler state management (one entry per blog)
    - Easier reprocessing (just change status)
    - Better performance (no complex queries)
    - Cleaner worker polling
    """
    request_id = getattr(request.state, 'request_id', None) or generate_request_id()
    
    try:
        # Normalize the URL
        normalized_url = normalize_url(blog_url)
        logger.info(f"[{request_id}] 🔍 [V2] Check-and-load for URL: {normalized_url}")
        
        # Validate blog URL domain matches publisher's domain
        await validate_blog_url_domain(normalized_url, publisher)
        
        # Service is already injected via DI - no need to create it manually
        result_data = await blog_processing_service.check_and_load_questions(
            normalized_url=normalized_url,
            publisher=publisher,
            request_id=request_id,
        )

        return success_response(
            result=result_data,
            message=result_data.get("message", "Questions loaded successfully"),
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ [V2] HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ [V2] Failed to check and load: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to check and load questions",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )

