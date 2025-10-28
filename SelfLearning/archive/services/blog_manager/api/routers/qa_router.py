"""
Q&A router for the blog manager microservice.

Handles general question-answering endpoints.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse

from ...models.request_models import QuestionAnswerRequest
from ...models.response_models import QuestionAnswerResponse, ErrorResponse
from ...services.qa_service import QAService
from ...core.config import Settings, get_settings
from ...core.rate_limiting import limiter, RateLimits

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/qa",
    tags=["Q&A"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        429: {"model": ErrorResponse, "description": "Rate Limit Exceeded"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)

# Global Q&A service instance
_qa_service: QAService = None


async def get_qa_service(settings: Settings = Depends(get_settings)) -> QAService:
    """Get or create the Q&A service instance."""
    global _qa_service
    
    if _qa_service is None:
        _qa_service = QAService(settings)
        await _qa_service.initialize()
    
    return _qa_service


@router.post(
    "/ask",
    response_model=QuestionAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a general question",
    description="""
    Ask any general question and get an AI-generated answer.
    
    **Features:**
    - Simple API - just send your question
    - Crisp answers (max 200 words)
    - Optimized for clarity and usefulness
    - Fast response times
    - Production-ready with error handling
    
    **Use Cases:**
    - General knowledge questions
    - Technical explanations
    - How-to guides
    - Concept clarifications
    - Problem-solving assistance
    
    **Response Format:**
    The AI will provide a structured, informative answer within 200 words, optimized for readability.
    """,
    responses={
        200: {
            "description": "Successfully generated answer",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "question": "What are the benefits of using microservices?",
                        "answer": "Microservices offer several key benefits: 1) **Independent Scaling** - Scale services based on demand. 2) **Technology Flexibility** - Use different tech stacks per service. 3) **Fault Isolation** - Service failures don't affect others. 4) **Faster Development** - Small teams work independently. 5) **Easier Maintenance** - Smaller, focused codebases. However, they introduce complexity in communication and deployment.",
                        "word_count": 58,
                        "character_count": 387,
                        "ai_model": "gpt-4",
                        "processing_time_ms": 1250.5
                    }
                }
            }
        },
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "VALIDATION_ERROR",
                        "message": "Question must be at least 5 characters long",
                        "details": {"field": "question", "value": "Hi?"}
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "details": {"retry_after_seconds": 60}
                    }
                }
            }
        }
    }
)
@limiter.limit(RateLimits.AI_GENERATION)  # 10 requests per minute for AI operations
async def ask_question(
    request: Request,
    question_request: QuestionAnswerRequest,
    qa_service: QAService = Depends(get_qa_service)
) -> QuestionAnswerResponse:
    """
    Generate an AI answer to any question.
    
    Args:
        request: The question and parameters
        qa_service: Injected Q&A service
        
    Returns:
        QuestionAnswerResponse with the generated answer
        
    Raises:
        HTTPException: For various error conditions
    """
    try:
        logger.info(f"Received Q&A request: {question_request.question[:100]}...")
        
        # Generate answer
        response = await qa_service.answer_question(question_request)
        
        logger.info(f"Successfully generated answer with {response.word_count} words")
        return response
        
    except ValueError as e:
        # Validation errors
        logger.warning(f"Validation error: {e}")
        error_response = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message=str(e),
            details={"question": question_request.question[:100]}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.model_dump(mode='json')
        )
        
    except Exception as e:
        error_msg = str(e)
        
        # Handle rate limiting
        if "rate limit" in error_msg.lower():
            logger.warning(f"Rate limit exceeded: {e}")
            error_response = ErrorResponse(
                error_code="RATE_LIMIT_EXCEEDED",
                message="Too many requests. Please try again later.",
                details={"retry_after_seconds": 60}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_response.model_dump(mode='json')
            )
        
        # Handle service unavailable
        if "unavailable" in error_msg.lower() or "configuration" in error_msg.lower():
            logger.error(f"Service unavailable: {e}")
            error_response = ErrorResponse(
                error_code="SERVICE_UNAVAILABLE",
                message="AI service is temporarily unavailable. Please try again later.",
                details={"error": error_msg}
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_response.model_dump(mode='json')
            )
        
        # Generic server error
        logger.error(f"Unexpected error in Q&A endpoint: {e}")
        error_response = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred while processing your question.",
            details={"error": error_msg}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )


@router.get(
    "/health",
    summary="Q&A service health check",
    description="Check the health status of the Q&A service and its dependencies.",
    responses={
        200: {
            "description": "Service health information",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "llm_service": "healthy",
                        "available_providers": ["openai", "anthropic"],
                        "healthy_providers": ["openai"]
                    }
                }
            }
        }
    }
)
async def qa_health_check(
    qa_service: QAService = Depends(get_qa_service)
) -> Dict[str, Any]:
    """
    Check the health of the Q&A service.
    
    Args:
        qa_service: Injected Q&A service
        
    Returns:
        Health status information
    """
    try:
        health_info = await qa_service.health_check()
        return health_info
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
