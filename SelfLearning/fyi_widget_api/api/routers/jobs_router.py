"""Jobs router - handles job enqueueing and status."""

import logging
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

# Add shared to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from fyi_widget_shared_library.models.job_queue import JobCreateRequest, JobStatusResponse, JobStatus
from fyi_widget_shared_library.models import ProcessJobResponse, SwaggerJobStatusResponse, JobStatsResponse, StandardErrorResponse, StandardSuccessResponse
from fyi_widget_shared_library.data.job_repository import JobRepository
from fyi_widget_shared_library.data.postgres_database import PostgresPublisherRepository
from fyi_widget_shared_library.models.publisher import PublisherStatus, Publisher
from fyi_widget_shared_library.utils import (
    normalize_url,
    success_response,
    handle_http_exception,
    handle_generic_exception,
    generate_request_id
)

# Import auth
from fyi_widget_api.api.auth import get_current_publisher, validate_blog_url_domain, verify_admin_key
# Enforcement helpers
from fyi_widget_api.api.publisher_rules import ensure_url_whitelisted
from fyi_widget_shared_library.data.postgres_database import UsageLimitExceededError
from fyi_widget_api.api import auth as auth_module

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get database
async def get_job_repository() -> JobRepository:
    """Get job repository instance."""
    from fyi_widget_api.api.main import db_manager
    return JobRepository(db_manager.database)


# Dependency to get publisher repository
async def get_publisher_repository() -> PostgresPublisherRepository:
    """Get publisher repository instance."""
    from fyi_widget_api.api.main import publisher_repo_instance
    if not publisher_repo_instance:
        raise HTTPException(
            status_code=500,
            detail="Publisher repository not initialized"
        )
    return publisher_repo_instance


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url if url.startswith('http') else f'https://{url}')
    domain = parsed.netloc or parsed.path
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain.lower()


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
    job_repo: JobRepository = Depends(get_job_repository)
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
        # Normalize URL to handle www, trailing slashes, etc.
        normalized_url = normalize_url(request.blog_url)
        logger.info(f"[{request_id}] 📥 Enqueueing blog: {request.blog_url}")
        if normalized_url != request.blog_url:
            logger.info(f"[{request_id}]    Normalized to: {normalized_url}")
        
        # Validate blog URL domain matches publisher's domain
        await validate_blog_url_domain(normalized_url, publisher)
        logger.info(f"[{request_id}] ✅ Publisher authenticated: {publisher.name} ({publisher.domain})")
        
        # Check daily blog limit
        if publisher.config.daily_blog_limit:
            # Get today's start (midnight)
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Count jobs processed today for this domain
            jobs_today = await job_repo.collection.count_documents({
                "blog_url": {"$regex": f"^https?://(www\\.)?{publisher.domain}"},
                "status": "completed",
                "completed_at": {"$gte": today_start}
            })
            
            logger.info(f"📊 Daily usage: {jobs_today}/{publisher.config.daily_blog_limit}")
            
            if jobs_today >= publisher.config.daily_blog_limit:
                logger.warning(f"❌ Daily limit exceeded: {jobs_today}/{publisher.config.daily_blog_limit}")
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily blog processing limit reached ({publisher.config.daily_blog_limit}). "
                           f"Please try again tomorrow or upgrade your plan."
                )
        
        logger.info(f"✅ Publisher validation passed for: {publisher.name}")
        
        # Check if blog already exists and has been successfully processed
        from fyi_widget_api.api.main import db_manager
        blogs_collection = db_manager.database["raw_blog_content"]
        existing_blog = await blogs_collection.find_one({"url": normalized_url})
        
        if existing_blog:
            logger.info(f"✅ Blog already exists: {request.blog_url}")
            
            # Check if there's a completed job for this URL (using normalized URL)
            existing_job = await job_repo.collection.find_one({
                "blog_url": normalized_url,
                "status": "completed"
            })
            
            if existing_job:
                logger.info(f"[{request_id}] ✅ Returning existing completed job: {existing_job['job_id']}")
                
                # Return existing completed job
                from fyi_widget_shared_library.models import ProcessingJob
                job = ProcessingJob(**existing_job)
                
                job_response = JobStatusResponse(
                    job_id=job.job_id,
                    blog_url=job.blog_url,
                    status=job.status,
                    failure_count=job.failure_count,
                    error_message=job.error_message,
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    processing_time_seconds=job.processing_time_seconds,
                    result=job.result
                )
                
                return success_response(
                    result=job_response.model_dump(),
                    message="Blog already processed, returning existing job",
                    status_code=200,
                    request_id=request_id
                )
            
            logger.info(f"⚠️  Blog exists but no completed job found, will reprocess")
        
        # Blog doesn't exist or wasn't successfully processed - enforce limits and enqueue new job
        ensure_url_whitelisted(normalized_url, publisher)

        slot_reserved = False
        try:
            if auth_module.publisher_repo:
                await auth_module.publisher_repo.reserve_blog_slot(publisher.id)
                slot_reserved = True
            # Pass publisher_id and config so worker can release the slot properly
            job = await job_repo.enqueue_job(
                normalized_url,
                publisher_id=publisher.id,
                config=publisher.config.model_dump() if publisher.config else None
            )
        except UsageLimitExceededError as exc:
            logger.warning(f"[{request_id}] ❌ Blog limit reached for publisher {publisher.id}: {exc}")
            raise HTTPException(
                status_code=403,
                detail=str(exc),
            )
        except Exception as enqueue_error:
            if slot_reserved and auth_module.publisher_repo:
                try:
                    await auth_module.publisher_repo.release_blog_slot(
                        publisher.id,
                        processed=False,
                    )
                except Exception as release_error:  # pragma: no cover - logging only
                    logger.warning(f"[{request_id}] ⚠️ Failed to release reserved blog slot: {release_error}")
            raise
        
        job_response = JobStatusResponse(
            job_id=job.job_id,
            blog_url=job.blog_url,
            status=job.status,
            failure_count=job.failure_count,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            processing_time_seconds=job.processing_time_seconds,
            result=job.result
        )
        
        return success_response(
            result=job_response.model_dump(),
            message="Blog processing job enqueued successfully",
            status_code=202,
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
        
        job = await job_repo.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job not found: {job_id}"
            )
        
        job_response = JobStatusResponse(
            job_id=job.job_id,
            blog_url=job.blog_url,
            status=job.status,
            failure_count=job.failure_count,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            processing_time_seconds=job.processing_time_seconds,
            result=job.result,
            updated_at=job.updated_at if hasattr(job, 'updated_at') else None
        )
        
        # Convert to dict and serialize datetime fields
        result_data = job_response.model_dump()
        
        # Serialize datetime fields to ISO format strings
        for field in ['created_at', 'started_at', 'completed_at', 'updated_at']:
            if field in result_data and result_data[field]:
                if hasattr(result_data[field], 'isoformat'):
                    result_data[field] = result_data[field].isoformat()
        
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
        
        stats = await job_repo.get_job_stats()
        result_data = {
            "queue_stats": stats,
            "total_jobs": sum(stats.values())
        }
        
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
        
        success = await job_repo.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Job cannot be cancelled (may already be processing or completed)"
            )
        
        result_data = {
            "job_id": job_id,
            "cancelled": True
        }
        
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

