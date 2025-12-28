"""Questions router - handles question retrieval."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fyi_widget_api.api.models import QuestionsByUrlResponse, QuestionByIdResponse, CheckAndLoadResponse, StandardErrorResponse
from fyi_widget_api.api.models.publisher_models import Publisher
from fyi_widget_api.api.repositories import JobRepository, QuestionRepository
from fyi_widget_api.api.utils import (
    normalize_url,
    success_response,
    handle_http_exception,
    handle_generic_exception,
    generate_request_id,
    extract_domain
)

# Import auth/deps
from fyi_widget_api.api.auth import get_current_publisher, verify_admin_key
from fyi_widget_api.api.services.auth_service import validate_blog_url_domain
from fyi_widget_api.api.deps import get_job_repository, get_question_repository, get_publisher_repo
from fyi_widget_api.api.repositories import PublisherRepository
from fyi_widget_api.api.services.question_service import QuestionService

logger = logging.getLogger(__name__)

router = APIRouter()


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
    publisher: Publisher = Depends(get_current_publisher),
    question_repo: QuestionRepository = Depends(get_question_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    publisher_repo: PublisherRepository = Depends(get_publisher_repo),
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
        
        # Instantiate service with injected dependencies
        question_service = QuestionService(
            question_repo=question_repo,
            job_repo=job_repo,
            publisher_repo=publisher_repo,
        )
        
        result_data = await question_service.check_and_load_questions(
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
    publisher: Publisher = Depends(get_current_publisher),
    question_repo: QuestionRepository = Depends(get_question_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    publisher_repo: PublisherRepository = Depends(get_publisher_repo),
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
        blog_domain = extract_domain(normalized_url).lower()
        
        logger.info(f"[{request_id}] 📖 Getting questions for URL: {normalized_url}")
        
        # Validate blog URL domain matches publisher's domain
        await validate_blog_url_domain(normalized_url, publisher)
        logger.info(f"[{request_id}] ✅ Publisher authenticated: {publisher.name} ({publisher.domain})")
        
        # Instantiate service with injected dependencies
        question_service = QuestionService(
            question_repo=question_repo,
            job_repo=job_repo,
            publisher_repo=publisher_repo,
        )
        
        result_data = await question_service.get_questions_by_url(
            normalized_url=normalized_url,
            publisher=publisher,
            request_id=request_id,
            original_blog_url=blog_url,
        )

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
    blog_id: str,
    question_repo: QuestionRepository = Depends(get_question_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    publisher_repo: PublisherRepository = Depends(get_publisher_repo),
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
        
        # Instantiate service with injected dependencies
        question_service = QuestionService(
            question_repo=question_repo,
            job_repo=job_repo,
            publisher_repo=publisher_repo,
        )
        
        deletion_result = await question_service.delete_blog_by_id(
            blog_id=blog_id,
            request_id=request_id,
        )
        
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
    publisher: Publisher = Depends(get_current_publisher),
    question_repo: QuestionRepository = Depends(get_question_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    publisher_repo: PublisherRepository = Depends(get_publisher_repo),
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
        
        # Instantiate service with injected dependencies
        question_service = QuestionService(
            question_repo=question_repo,
            job_repo=job_repo,
            publisher_repo=publisher_repo,
        )
        
        question = await question_service.get_question_by_id(
            question_id=question_id,
            request_id=request_id,
        )

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
