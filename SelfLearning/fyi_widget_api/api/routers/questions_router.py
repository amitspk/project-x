"""Questions router - handles question retrieval."""

import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from bson import ObjectId

# Add shared to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from fyi_widget_shared_library.services import StorageService
from fyi_widget_shared_library.models import QuestionsByUrlResponse, QuestionByIdResponse, CheckAndLoadResponse, StandardErrorResponse
from fyi_widget_shared_library.models.publisher import Publisher
from fyi_widget_shared_library.models.job_queue import JobStatus
from fyi_widget_shared_library.data.job_repository import JobRepository
from fyi_widget_shared_library.utils import (
    normalize_url,
    success_response,
    handle_http_exception,
    handle_generic_exception,
    generate_request_id
)

# Import auth
from fyi_widget_api.api.auth import get_current_publisher, validate_blog_url_domain, verify_admin_key
from fyi_widget_api.api.publisher_rules import ensure_url_whitelisted
from fyi_widget_shared_library.data.postgres_database import UsageLimitExceededError

logger = logging.getLogger(__name__)

router = APIRouter()

# Storage service will be initialized per-request with database
def get_storage():
    from fyi_widget_api.api.main import db_manager
    return StorageService(database=db_manager.database)

# Job repository will be initialized per-request
async def get_job_repository() -> JobRepository:
    """Get job repository instance."""
    from fyi_widget_api.api.main import db_manager
    return JobRepository(db_manager.database)


@router.get(
    "/check-and-load",
    response_model=CheckAndLoadResponse,
    responses={
        200: {"description": "Questions ready or processing initiated"},
        401: {"model": StandardErrorResponse, "description": "Authentication required"},
        403: {"model": StandardErrorResponse, "description": "Publisher account not active or domain mismatch"}
    }
)
async def check_and_load_questions(
    request: Request,
    blog_url: str = Query(..., description="The blog URL to check and load questions for"),
    publisher: Publisher = Depends(get_current_publisher)
) -> Dict[str, Any]:
    """
    Intelligent endpoint that checks if questions exist and loads them, or initiates processing.
    
    **Authentication**: Requires X-API-Key header with valid publisher API key.
    
    **Smart Loading Strategy**:
    1. First checks if questions already exist for the URL
    2. If YES → Returns questions immediately (fast path ⚡)
    3. If NO → Checks if processing job exists
    4. If job exists → Returns job status
    5. If no job → Auto-creates processing job
    
    **Response States**:
    - `ready`: Questions are available and returned
    - `processing`: Job is currently processing (returns job_id)
    - `not_started`: New job created (returns job_id)
    - `failed`: Previous processing failed (can retry)
    
    **Benefits**:
    - Single API call for UI
    - Optimal performance (returns cached questions if available)
    - Automatic job creation if needed
    - No duplicate processing jobs
    """
    request_id = getattr(request.state, 'request_id', None) or generate_request_id()
    
    try:
        # Normalize the URL
        normalized_url = normalize_url(blog_url)
        logger.info(f"[{request_id}] 🔍 Check-and-load for URL: {normalized_url}")
        
        # Validate blog URL domain matches publisher's domain
        await validate_blog_url_domain(normalized_url, publisher)
        
        storage = get_storage()
        job_repo = await get_job_repository()
        
        # STEP 1: Check if questions already exist (FAST PATH)
        questions = await storage.get_questions_by_url(normalized_url, limit=None)
        
        if questions and len(questions) > 0:
            # Questions exist! Return them immediately
            logger.info(f"[{request_id}] ⚡ Fast path: {len(questions)} questions found, returning immediately")

            # Randomize questions
            import random
            questions_copy = list(questions)
            random.shuffle(questions_copy)
            
            # Get blog metadata
            blog_info = await storage.get_blog_by_url(normalized_url)
            blog_id = questions_copy[0].blog_id
            
            # Convert questions to response format
            questions_response = []
            for q in questions_copy:
                # Get all fields and explicitly build response dict (exclude unwanted fields completely)
                q_dict = q.model_dump() if hasattr(q, 'model_dump') else q.dict()
                # Build new dict with only the fields we want
                response_dict = {
                    'id': q_dict.get('id'),
                    'question': q_dict.get('question'),
                    'answer': q_dict.get('answer')
                }
                questions_response.append(response_dict)
            
            result_data = {
                "processing_status": "ready",
                "blog_url": normalized_url,
                "questions": questions_response,
                "blog_info": {
                    "id": blog_id,
                    "title": blog_info.get("title", "") if blog_info else "",
                    "url": normalized_url,
                    "author": blog_info.get("author", "") if blog_info else "",
                    "published_date": blog_info.get("published_date", "") if blog_info else "",
                    "question_count": len(questions_response)
                },
                "job_id": None,
                "message": "Questions ready - loaded from cache"
            }
            
            return success_response(
                result=result_data,
                message="Questions loaded successfully",
                status_code=200,
                request_id=request_id
            )
        
        # STEP 2: No questions found - Check if processing job exists
        logger.info(f"[{request_id}] 🔄 No questions found, checking for existing job")
        
        # Check for existing active job (pending or processing)
        # Allow immediate requeuing of skipped jobs - they can be requeued right away
        existing_job = await job_repo.collection.find_one({
            "blog_url": normalized_url,
            "status": {"$in": ["pending", "processing"]}
        }, sort=[("created_at", -1)])
        
        if existing_job:
            job_status = existing_job.get("status")
            job_id = str(existing_job.get("_id"))
            
            if job_status == "processing":
                logger.info(f"[{request_id}] ⏳ Job already processing: {job_id}")
                result_data = {
                    "processing_status": "processing",
                    "blog_url": normalized_url,
                    "questions": None,
                    "blog_info": None,
                    "job_id": job_id,
                    "message": "Blog is currently being processed"
                }
            elif job_status == "pending":
                logger.info(f"[{request_id}] ⏳ Job pending: {job_id}")
                result_data = {
                    "processing_status": "processing",
                    "blog_url": normalized_url,
                    "questions": None,
                    "blog_info": None,
                    "job_id": job_id,
                    "message": "Blog processing is queued"
                }
            
            # Return early if we have an active job (processing or pending)
            # Skipped jobs are NOT included in the query, so they can be immediately requeued
            return success_response(
                result=result_data,
                message="Job status retrieved",
                status_code=200,
                request_id=request_id
            )
        
        # STEP 3: No active job - Create new processing job
        # This includes cases where: no job exists, job was skipped, or job failed
        # Skipped jobs can be immediately requeued
        from fyi_widget_shared_library.models.job_queue import JobCreateRequest, JobStatus
        from datetime import datetime
        
        logger.info(f"[{request_id}] 🚀 Creating new processing job")
        
        # Get publisher config
        from fyi_widget_api.api import auth as auth_module
        publisher_config = publisher.config.dict() if publisher.config else {}
        
        ensure_url_whitelisted(normalized_url, publisher)

        # Create job
        slot_reserved = False
        try:
            if auth_module.publisher_repo:
                await auth_module.publisher_repo.reserve_blog_slot(publisher.id)
                slot_reserved = True

            job_id = await job_repo.create_job(
                blog_url=normalized_url,
                publisher_id=publisher.id,
                config=publisher_config
            )
        except UsageLimitExceededError as exc:
            logger.warning(f"[{request_id}] ❌ Blog limit reached for publisher {publisher.id}: {exc}")
            raise HTTPException(
                status_code=403,
                detail=str(exc),
            )
        except Exception:
            if slot_reserved and auth_module.publisher_repo:
                try:
                    await auth_module.publisher_repo.release_blog_slot(
                        publisher.id,
                        processed=False,
                    )
                except Exception as release_error:  # pragma: no cover - logging only
                    logger.warning(f"[{request_id}] ⚠️ Failed to release reserved blog slot: {release_error}")
            raise
        
        # Note: Usage tracking (blogs_processed) will be handled by worker when job completes
        # This prevents double counting since worker also increments on completion
        
        logger.info(f"[{request_id}] ✅ Processing job created: {job_id}")
        
        result_data = {
            "processing_status": "not_started",
            "blog_url": normalized_url,
            "questions": None,
            "blog_info": None,
            "job_id": job_id,
            "message": "Processing started - check back in 30-60 seconds"
        }
        
        return success_response(
            result=result_data,
            message=result_data["message"],
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
        logger.error(f"[{request_id}] ❌ Failed to check and load: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to check and load questions",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/by-url",
    response_model=QuestionsByUrlResponse,
    responses={
        200: {"description": "Questions retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Authentication required - X-API-Key header missing"},
        403: {"model": StandardErrorResponse, "description": "Publisher account not active or domain mismatch"},
        404: {"model": StandardErrorResponse, "description": "No questions found for the given URL"}
    }
)
async def get_questions_by_url(
    request: Request,
    blog_url: str = Query(..., description="The blog URL to get questions for"),
    publisher: Publisher = Depends(get_current_publisher)
) -> Dict[str, Any]:
    """
    Get all questions for a specific blog URL.
    
    **Authentication**: Requires X-API-Key header with valid publisher API key.
    
    Questions are randomized on each request for better user experience.
    
    Returns standardized format:
    {
        "status": "success",
        "status_code": 200,
        "message": "Questions retrieved successfully",
        "result": {...},
        "request_id": "req_abc123",
        "timestamp": "2025-10-18T14:30:00.123Z"
    }
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(request.state, 'request_id', None) or generate_request_id()
    
    publisher_name = publisher.name.lower()
    blog_domain = None
    
    try:
        # Normalize the URL for consistent lookups
        normalized_url = normalize_url(blog_url)
        from fyi_widget_shared_library.utils.url_utils import extract_domain
        blog_domain = extract_domain(normalized_url).lower()
        
        logger.info(f"[{request_id}] 📖 Getting questions for URL: {normalized_url}")
        
        # Validate blog URL domain matches publisher's domain
        await validate_blog_url_domain(normalized_url, publisher)
        logger.info(f"[{request_id}] ✅ Publisher authenticated: {publisher.name} ({publisher.domain})")
        
        storage = get_storage()
        # Get all questions (no limit)
        questions = await storage.get_questions_by_url(normalized_url, limit=None)
        
        if not questions:
            # Record metrics for not found
            raise HTTPException(
                status_code=404,
                detail=f"No questions found for URL: {blog_url}"
            )
        
        # Always randomize questions
        import random
        questions_copy = list(questions)  # Create a copy to avoid modifying original
        random.shuffle(questions_copy)
        questions = questions_copy
        logger.info(f"[{request_id}] 🔀 Returning {len(questions)} questions (randomized)")
        
        # Get blog metadata (using normalized URL)
        blog_info = await storage.get_blog_by_url(normalized_url)
        
        # Extract blog_id from first question for blog_info
        blog_id = questions[0].blog_id
        
        # Convert questions to dict and exclude embedding, blog_url, blog_id fields for response
        questions_response = []
        for q in questions:
            # Build new dict with only the fields we want (completely exclude unwanted fields)
            q_dict = q.model_dump() if hasattr(q, 'model_dump') else q.dict()
            response_dict = {
                'id': q_dict.get('id'),
                'question': q_dict.get('question'),
                'answer': q_dict.get('answer')
            }
            questions_response.append(response_dict)
        
        # Format result data
        result_data = {
            "questions": questions_response,
            "blog_info": {
                "id": blog_id,
                "title": blog_info.get("title", "") if blog_info else "",
                "url": blog_url,
                "author": blog_info.get("author", "") if blog_info else "",
                "published_date": blog_info.get("published_date", "") if blog_info else "",
                "question_count": len(questions)
            }
        }
        
        # Return standardized success response
        return success_response(
            result=result_data,
            message="Questions retrieved successfully",
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
        logger.error(f"[{request_id}] ❌ Failed to get questions by URL: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to retrieve questions",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.delete(
    "/{blog_id}",
    dependencies=[Depends(verify_admin_key)],
    responses={
        200: {"description": "Blog and associated data deleted successfully"},
        401: {"model": StandardErrorResponse, "description": "Admin authentication required - X-Admin-Key header missing"},
        404: {"model": StandardErrorResponse, "description": "Blog not found"},
        400: {"model": StandardErrorResponse, "description": "Invalid blog_id format"}
    }
)
async def delete_blog_by_id(
    request: Request,
    blog_id: str
) -> Dict[str, Any]:
    """
    Delete a blog and all associated data (questions, summary, content) by blog_id.
    
    **Admin Only**: Requires X-Admin-Key header for authentication.
    
    **⚠️ WARNING**: This is a destructive operation that cannot be undone!
    
    Deletes:
    - Blog content
    - All questions/answers generated for this blog
    - Summary and embeddings
    
    **Use Cases**:
    - Remove outdated or incorrect content
    - Clean up test data
    - Comply with data deletion requests
    
    Returns deletion summary with counts of deleted items.
    """
    request_id = getattr(request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 🗑️  Admin delete request for blog_id: {blog_id}")
        
        storage = get_storage()
        
        # Validate blog_id format
        try:
            ObjectId(blog_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid blog_id format: {blog_id}"
            )
        
        # Check if blog exists
        blogs_collection = storage.database[storage.blogs_collection]
        blog = await blogs_collection.find_one({"_id": ObjectId(blog_id)})
        if not blog:
            raise HTTPException(
                status_code=404,
                detail=f"Blog not found with id: {blog_id}"
            )
        
        # Delete blog and all associated data
        deletion_result = await storage.delete_blog(blog_id)
        
        logger.info(
            f"[{request_id}] ✅ Blog deleted: "
            f"blog={deletion_result['blog_deleted']}, "
            f"questions={deletion_result['questions_deleted']}, "
            f"summary={deletion_result['summary_deleted']}"
        )
        
        # Return standardized success response
        return success_response(
            result=deletion_result,
            message="Blog and associated data deleted successfully",
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
        logger.error(f"[{request_id}] ❌ Failed to delete blog: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to delete blog",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )


@router.get(
    "/{question_id}",
    response_model=QuestionByIdResponse,
    responses={
        200: {"description": "Question retrieved successfully"},
        401: {"model": StandardErrorResponse, "description": "Authentication required - X-API-Key header missing"},
        403: {"model": StandardErrorResponse, "description": "Publisher account not active"},
        404: {"model": StandardErrorResponse, "description": "Question not found"}
    }
)
async def get_question_by_id(
    request: Request,
    question_id: str,
    publisher: Publisher = Depends(get_current_publisher)
) -> Dict[str, Any]:
    """
    Get a specific question by ID.
    
    **Authentication**: Requires X-API-Key header with valid publisher API key.
    
    Returns standardized format:
    {
        "status": "success",
        "status_code": 200,
        "message": "Question retrieved successfully",
        "result": {...},
        "request_id": "req_abc123",
        "timestamp": "2025-10-18T14:30:00.123Z"
    }
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(request.state, 'request_id', None) or generate_request_id()
    
    try:
        logger.info(f"[{request_id}] 📖 Getting question by ID: {question_id}")
        
        storage = get_storage()
        question = await storage.get_question_by_id(question_id)
        
        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question not found: {question_id}"
            )
        
        # Convert ObjectId to string and rename _id to id
        question["id"] = str(question["_id"])
        question.pop("_id", None)
        
        # Remove embedding field to reduce response size
        question.pop('embedding', None)
        
        # Remove click_count from response (internal tracking only)
        question.pop('click_count', None)
        question.pop('last_clicked_at', None)
        
        # Remove icon if present (should not be in schema, but remove for safety)
        question.pop('icon', None)
        
        # Keep keyword_anchor and probability for this endpoint (single question details)
        # Convert datetime to ISO format string (keep created_at for this endpoint)
        if 'created_at' in question and question['created_at']:
            if hasattr(question['created_at'], 'isoformat'):
                question['created_at'] = question['created_at'].isoformat()
        
        # Return standardized success response
        return success_response(
            result=question,
            message="Question retrieved successfully",
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
        logger.error(f"[{request_id}] ❌ Failed to get question: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to retrieve question",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
