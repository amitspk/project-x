"""Blogs router - handles blog processing operations."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fyi_widget_api.api.models.job_models import JobCreateRequest
from fyi_widget_api.api.models import ProcessJobResponse, JobStatsResponse, StandardErrorResponse, StandardSuccessResponse
from fyi_widget_api.api.models.swagger_models import JobStatusResponse as SwaggerJobStatusResponse
from fyi_widget_api.api.repositories import JobRepository, PublisherRepository
from fyi_widget_api.api.models.publisher_models import Publisher
from fyi_widget_api.api.utils import (
    success_response,
    handle_http_exception,
    handle_generic_exception,
    generate_request_id
)

# Import auth
from fyi_widget_api.api.auth import get_current_publisher, verify_admin_key
from fyi_widget_api.api.services.auth_service import validate_blog_url_domain
# DI providers
from fyi_widget_api.api.deps import get_job_repository, get_publisher_repo
from fyi_widget_api.api.services.blog_service import BlogService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/process",
    status_code=202,
    response_model=ProcessJobResponse,
    responses={
        202: {"description": "Blog processing job enqueued successfully"},
        400: {"model": StandardErrorResponse, "description": "Invalid blog URL"},
        401: {"model": StandardErrorResponse, "description": "Authentication required - X-API-Key header missing"},
        403: {"model": StandardErrorResponse, "description": "Domain mismatch or daily limit exceeded"}
    }
)
async def enqueue_blog_processing(
    http_request: Request,
    request: JobCreateRequest,
    publisher: Publisher = Depends(get_current_publisher),
    job_repo: JobRepository = Depends(get_job_repository),
    publisher_repo: PublisherRepository = Depends(get_publisher_repo),
) -> Dict[str, Any]:
    """
    Enqueue a blog for processing.
    
    **Authentication:**
    - Requires X-API-Key header with valid publisher API key
    - Blog URL domain must match publisher's registered domain
    
    **Rate Limiting:**
    - Daily blog processing limit enforced per publisher
    - Trial accounts have lower limits
    
    Returns standardized 202 Accepted response with job_id for tracking.
    The actual processing will be done asynchronously by the worker service.
    
    If the blog has already been processed, returns the existing completed job
    instead of creating a duplicate.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        # Validate blog URL domain matches publisher's domain
        await validate_blog_url_domain(request.blog_url, publisher)
        logger.info(f"[{request_id}] ✅ Publisher authenticated: {publisher.name} ({publisher.domain})")

        job_service = BlogService(job_repo=job_repo, publisher_repo=publisher_repo)
        result_data, status_code, message = await job_service.enqueue_blog_processing(
            blog_url=request.blog_url,
            publisher=publisher,
            request_id=request_id,
        )

        return success_response(
            result=result_data,
            message=message,
            status_code=status_code,
            request_id=request_id
        )
        
    except HTTPException as exc:
        # Record metrics for error (if not already recorded)
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to enqueue job: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to enqueue job",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/status/{job_id}",
    response_model=SwaggerJobStatusResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Job status retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required - X-Admin-Key header missing"},
        404: {"model": StandardErrorResponse, "description": "Job not found"}
    }
)
async def get_job_status(
    http_request: Request,
    job_id: str,
    job_repo: JobRepository = Depends(get_job_repository)
) -> Dict[str, Any]:
    """
    Get the status of a processing job.
    
    **Admin Only**: This endpoint requires admin authentication (X-Admin-Key header).
    
    Returns job details including status, timestamps, error messages (if any),
    and processing results.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📊 Getting job status: {job_id}")
        
        job_service = BlogService(job_repo=job_repo, publisher_repo=None)
        result_data = await job_service.get_job_status(
            job_id=job_id,
            request_id=request_id,
        )

        return success_response(
            result=result_data,
            message="Job status retrieved successfully",
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
        logger.error(f"[{request_id}] ❌ Failed to get job status: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to get job status",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/stats",
    response_model=JobStatsResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Queue statistics retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"}
    }
)
async def get_queue_stats(
    http_request: Request,
    job_repo: JobRepository = Depends(get_job_repository)
) -> Dict[str, Any]:
    """
    Get statistics about the job queue.
    
    **Admin Only**: This endpoint requires admin authentication (X-Admin-Key header).
    
    Returns aggregated statistics about job processing including counts by status
    (pending, processing, completed, failed) and total job count.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📊 Getting queue stats")
        
        job_service = BlogService(job_repo=job_repo, publisher_repo=None)
        result_data = await job_service.get_queue_stats()
        
        return success_response(
            result=result_data,
            message="Queue statistics retrieved successfully",
            status_code=200,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] ❌ Failed to get queue stats: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to get queue stats",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.post(
    "/cancel/{job_id}",
    response_model=StandardSuccessResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Job cancelled successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required"},
        404: {"model": StandardErrorResponse, "description": "Job not found or cannot be cancelled"}
    }
)
async def cancel_job(
    http_request: Request,
    job_id: str,
    job_repo: JobRepository = Depends(get_job_repository)
) -> Dict[str, Any]:
    """
    Cancel a queued job.
    
    **Admin Only**: This endpoint requires admin authentication (X-Admin-Key header).
    
    Jobs can only be cancelled if they are in 'pending' or 'queued' status.
    Jobs that are already processing or completed cannot be cancelled.
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()

    try:
        logger.info(f"[{request_id}] 🚫 Cancelling job: {job_id}")
        
        job_service = BlogService(job_repo=job_repo, publisher_repo=None)
        result_data = await job_service.cancel_job(
            job_id=job_id,
            request_id=request_id,
        )
        
        return success_response(
            result=result_data,
            message=f"Job {job_id} cancelled successfully",
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
        logger.error(f"[{request_id}] ❌ Failed to cancel job: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to cancel job",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )

