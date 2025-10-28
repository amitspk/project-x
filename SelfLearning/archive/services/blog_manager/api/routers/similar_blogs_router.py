"""
Similar blogs router for the blog manager microservice.

Handles endpoints for finding similar blogs based on question embeddings.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse

from ...models.request_models import SimilarBlogsRequest
from ...models.response_models import SimilarBlogsResponse, ErrorResponse
from ...services.similar_blogs_service import SimilarBlogsService
from ...core.config import Settings, get_settings
from ...core.rate_limiting import limiter, RateLimits

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/similar",
    tags=["Similar Blogs"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Question Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)

# Global similar blogs service instance
_similar_blogs_service: SimilarBlogsService = None


async def get_similar_blogs_service(settings: Settings = Depends(get_settings)) -> SimilarBlogsService:
    """Get or create the similar blogs service instance."""
    global _similar_blogs_service
    
    if _similar_blogs_service is None:
        _similar_blogs_service = SimilarBlogsService(settings)
        await _similar_blogs_service.initialize()
    
    return _similar_blogs_service


@router.post(
    "/blogs",
    response_model=SimilarBlogsResponse,
    status_code=status.HTTP_200_OK,
    summary="Find similar blogs by question ID",
    description="""
    Find blogs similar to a specific question based on semantic similarity.
    
    **How it works:**
    1. Takes a question ID from any blog
    2. Retrieves the question and answer text
    3. Generates embeddings for the question+answer combination
    4. Performs similarity search against all blog summary embeddings
    5. Returns the top 3 most similar blogs with similarity scores
    
    **Features:**
    - Semantic similarity search using embeddings
    - Excludes the current blog from results (if blog_url provided)
    - Returns similarity scores (0.0 to 1.0)
    - Includes blog metadata (title, author, word count, etc.)
    - Fast response times with embedding-based search
    
    **Use Cases:**
    - "Related Articles" recommendations
    - Content discovery based on user interests
    - Cross-blog content linking
    - Similar topic exploration
    
    **Response Format:**
    Returns similar blogs ranked by semantic similarity with detailed metadata.
    """,
    responses={
        200: {
            "description": "Successfully found similar blogs",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "question_id": "q1",
                        "question_text": "What are the benefits of using microservices architecture?",
                        "answer_text": "Microservices architecture offers several key benefits...",
                        "similar_blogs": [
                            {
                                "blog_id": "microservices_patterns_xyz789",
                                "title": "Advanced Microservices Design Patterns",
                                "url": "https://dev.to/author/microservices-patterns",
                                "similarity_score": 0.89,
                                "summary_snippet": "Explore proven microservices patterns for scalable applications...",
                                "author": "Jane Developer",
                                "word_count": 3200,
                                "source_domain": "dev.to"
                            }
                        ],
                        "total_found": 3,
                        "search_embedding_size": 1536,
                        "processing_time_ms": 245.7
                    }
                }
            }
        },
        404: {
            "description": "Question not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "QUESTION_NOT_FOUND",
                        "message": "Question with ID 'q999' not found",
                        "details": {"question_id": "q999"}
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "EMBEDDING_ERROR",
                        "message": "Failed to generate embeddings for similarity search",
                        "details": {"error": "LLM service unavailable"}
                    }
                }
            }
        }
    }
)
@limiter.limit(RateLimits.SIMILARITY_SEARCH)  # 20 requests per minute for similarity search
async def find_similar_blogs(
    http_request: Request,
    request: SimilarBlogsRequest,
    similar_blogs_service: SimilarBlogsService = Depends(get_similar_blogs_service)
) -> SimilarBlogsResponse:
    """
    Find blogs similar to a specific question.
    
    Args:
        request: The similar blogs request with question ID and parameters
        similar_blogs_service: Injected similar blogs service
        
    Returns:
        SimilarBlogsResponse with similar blogs and metadata
        
    Raises:
        HTTPException: For various error conditions
    """
    try:
        logger.info(f"Finding similar blogs for question ID: {request.question_id}")
        
        # Find similar blogs
        response = await similar_blogs_service.find_similar_blogs(request)
        
        logger.info(f"Found {len(response.similar_blogs)} similar blogs for question {request.question_id}")
        return response
        
    except ValueError as e:
        # Question not found or validation errors
        logger.warning(f"Question not found: {e}")
        error_response = ErrorResponse(
            error_code="QUESTION_NOT_FOUND",
            message=str(e),
            details={"question_id": request.question_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump(mode='json')
        )
        
    except Exception as e:
        error_msg = str(e)
        
        # Handle embedding/LLM service errors
        if "embedding" in error_msg.lower() or "llm" in error_msg.lower():
            logger.error(f"Embedding service error: {e}")
            error_response = ErrorResponse(
                error_code="EMBEDDING_ERROR",
                message="Failed to generate embeddings for similarity search",
                details={"error": error_msg}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_response.model_dump(mode='json')
            )
        
        # Handle database errors
        if "database" in error_msg.lower() or "mongodb" in error_msg.lower():
            logger.error(f"Database error: {e}")
            error_response = ErrorResponse(
                error_code="DATABASE_ERROR",
                message="Database error while searching for similar blogs",
                details={"error": error_msg}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_response.model_dump(mode='json')
            )
        
        # Generic server error
        logger.error(f"Unexpected error in similar blogs endpoint: {e}")
        error_response = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred while finding similar blogs",
            details={"error": error_msg}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )


@router.get(
    "/health",
    summary="Similar blogs service health check",
    description="Check the health status of the similar blogs service and its dependencies.",
    responses={
        200: {
            "description": "Service health information",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "database": "healthy",
                        "blogs_with_embeddings": 25,
                        "llm_service": "available"
                    }
                }
            }
        }
    }
)
async def similar_blogs_health_check(
    similar_blogs_service: SimilarBlogsService = Depends(get_similar_blogs_service)
) -> Dict[str, Any]:
    """
    Check the health of the similar blogs service.
    
    Args:
        similar_blogs_service: Injected similar blogs service
        
    Returns:
        Health status information
    """
    try:
        health_info = await similar_blogs_service.health_check()
        return health_info
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
