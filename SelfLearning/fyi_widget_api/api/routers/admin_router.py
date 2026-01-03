"""Admin router - administrative operations for blog processing."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends, Body, Security
from pydantic import BaseModel, Field

from fyi_widget_api.api.models import StandardErrorResponse, StandardSuccessResponse
from fyi_widget_api.api.models.publisher_models import Publisher
from fyi_widget_api.api.models.blog_processing_models import BlogProcessingQueueEntry
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
from fyi_widget_api.api.auth import verify_admin_key, get_current_publisher, admin_key_header

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency injection for repositories
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


# Dependency injection for service
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


# Request models
class ReprocessBlogRequest(BaseModel):
    """Request model for reprocessing a blog."""
    blog_url: str = Field(..., description="Blog URL to reprocess (will be normalized)")
    publisher_id: str = Field(..., description="Publisher ID who owns this blog")
    reason: str = Field(None, description="Optional reason for reprocessing")


@router.post(
    "/reprocess",
    dependencies=[Depends(verify_admin_key), Security(admin_key_header)],
    responses={
        200: {"model": StandardSuccessResponse, "description": "Blog requeued for reprocessing"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Blog not found in processing queue"},
        409: {"model": StandardErrorResponse, "description": "Blog is currently processing (cannot reprocess)"}
    }
)
async def reprocess_blog(
    request: Request,
    body: ReprocessBlogRequest = Body(...),
    blog_processing_service: BlogProcessingService = Depends(get_blog_processing_service),
) -> Dict[str, Any]:
    """
    **Admin Only** - Manually trigger reprocessing of a blog.
    
    **Authentication**: Requires X-Admin-Key header.
    
    **When to Use:**
    - Blog completed but questions are poor quality
    - Want to regenerate with updated LLM settings
    - Blog failed permanently but issue is now fixed
    
    **Business Rules:**
    - ✅ Can reprocess if status is "completed" or "failed"
    - ❌ Cannot reprocess if "queued", "processing", or "retry"
    - ✅ Resets attempt count to 0 (fresh start)
    - ✅ Reserves new slot if coming from "failed" state
    - ✅ Tracks reprocess count for audit
    
    **Example:**
    ```json
    {
      "blog_url": "https://example.com/article",
      "publisher_id": "pub_abc123",
      "reason": "Improve question quality"
    }
    ```
    """
    request_id = getattr(request.state, 'request_id', None) or generate_request_id()
    
    try:
        # Normalize the URL
        normalized_url = normalize_url(body.blog_url)
        logger.info(
            f"[{request_id}] 🔧 [ADMIN] Reprocess request: {normalized_url} "
            f"(publisher: {body.publisher_id}, reason: {body.reason or 'N/A'})"
        )
        
        # Get publisher (need for slot reservation)
        # Access publisher_repo through the service since it's already injected
        publisher = await blog_processing_service.publisher_repo.get_publisher_by_id(body.publisher_id)
        if not publisher:
            raise HTTPException(
                status_code=404,
                detail=f"Publisher not found: {body.publisher_id}"
            )
        
        # Service is already injected via DI - no need to create it manually
        result_data = await blog_processing_service.reprocess_blog(
            blog_url=normalized_url,
            publisher=publisher,
            reason=body.reason,
            request_id=request_id,
        )

        return success_response(
            result=result_data,
            message=result_data.get("message", "Blog requeued for reprocessing"),
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException as exc:
        logger.error(f"[{request_id}] ❌ [ADMIN] HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ [ADMIN] Reprocess failed: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to reprocess blog",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/queue-stats",
    dependencies=[Depends(verify_admin_key), Security(admin_key_header)],
    responses={
        200: {"description": "Queue statistics retrieved"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"}
    }
)
async def get_queue_stats(
    request: Request,
    blog_processing_service: BlogProcessingService = Depends(get_blog_processing_service),
) -> Dict[str, Any]:
    """
    **Admin Only** - Get blog processing queue statistics.
    
    **Authentication**: Requires X-Admin-Key header.
    
    Returns counts for each status:
    - queued: Waiting to be picked up by worker
    - processing: Currently being processed
    - retry: Waiting for retry after failure
    - completed: Successfully processed
    - failed: Permanently failed (3 attempts exhausted)
    - total: Total entries
    """
    request_id = getattr(request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📊 [ADMIN] Get queue stats")
        
        # Access queue_repo through the service since it's already injected
        stats = await blog_processing_service.queue_repo.get_stats()
        
        return success_response(
            result=stats,
            message="Queue statistics retrieved",
            status_code=200,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] ❌ [ADMIN] Failed to get stats: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to retrieve queue statistics",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/jobs/status",
    dependencies=[Depends(verify_admin_key), Security(admin_key_header)],
    response_model=StandardSuccessResponse,
    responses={
        200: {"description": "Blog processing status retrieved"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Blog not found in processing queue"}
    }
)
async def get_blog_status(
    request: Request,
    url: str,
    queue_repo: BlogProcessingQueueRepository = Depends(get_blog_queue_repository),
) -> Dict[str, Any]:
    """
    **Admin Only** - Get blog processing status by URL.
    
    **Authentication**: Requires X-Admin-Key header.
    
    Returns the current processing state of a blog from the blog_processing_queue collection.
    
    **Query Parameters:**
    - `url`: Blog URL (will be normalized before lookup)
    
    **Example:**
    ```
    GET /api/v1/admin/jobs/status?url=https://example.com/article
    ```
    
    **Response Fields:**
    - `url`: Blog URL
    - `publisher_id`: Publisher ID
    - `status`: Current status (queued, processing, retry, completed, failed)
    - `attempt_count`: Number of processing attempts
    - `worker_id`: Worker instance processing this (if any)
    - `last_error`: Last error message (if any)
    - `created_at`: When entry was created
    - `updated_at`: Last update timestamp
    - `started_at`: When current attempt started (if processing)
    - `completed_at`: When processing completed (if completed)
    - And other metadata fields
    """
    request_id = getattr(request.state, 'request_id', None) or generate_request_id()
    
    try:
        # Normalize the URL
        normalized_url = normalize_url(url)
        logger.info(f"[{request_id}] 📊 [ADMIN] Get blog status: {normalized_url}")
        
        # Get entry from queue
        entry = await queue_repo.get_by_url(normalized_url)
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Blog not found in processing queue: {normalized_url}"
            )
        
        # Convert to Pydantic model for validation and serialization
        # Remove MongoDB _id field if present
        entry_dict = {k: v for k, v in entry.items() if k != "_id"}
        queue_entry = BlogProcessingQueueEntry(**entry_dict)
        
        return success_response(
            result=queue_entry.model_dump(),
            message="Blog processing status retrieved",
            status_code=200,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] ❌ [ADMIN] Failed to get blog status: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to retrieve blog processing status",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )

