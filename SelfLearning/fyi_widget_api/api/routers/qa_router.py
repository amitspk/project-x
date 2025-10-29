"""Q&A router - handles custom question answering."""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

# Add shared to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from fyi_widget_shared_library.services import LLMService
from fyi_widget_shared_library.models import QAResponse as SwaggerQAResponse, StandardErrorResponse
from fyi_widget_shared_library.models.publisher import Publisher
from fyi_widget_shared_library.utils import (
    success_response,
    handle_http_exception,
    handle_generic_exception,
    generate_request_id
)

# Import auth
from fyi_widget_api.api.auth import get_current_publisher

logger = logging.getLogger(__name__)

router = APIRouter()

# LLM service will be initialized per-request
def get_llm_service():
    return LLMService()


class QARequest(BaseModel):
    """Request for Q&A endpoint."""
    question: str


class QAResponse(BaseModel):
    """Response for Q&A endpoint."""
    success: bool
    question: str
    answer: str
    word_count: int
    processing_time_ms: float


@router.post(
    "/ask",
    response_model=SwaggerQAResponse,
    responses={
        200: {"description": "Question answered successfully"},
        400: {"model": StandardErrorResponse, "description": "Invalid question or empty question"},
        401: {"model": StandardErrorResponse, "description": "Authentication required - X-API-Key header missing"},
        403: {"model": StandardErrorResponse, "description": "Publisher account not active"}
    }
)
async def ask_question(
    http_request: Request,
    request: QARequest,
    publisher: Publisher = Depends(get_current_publisher)
) -> Dict[str, Any]:
    """
    Answer a custom question using LLM.
    
    **Authentication**: Requires X-API-Key header with valid publisher API key.
    
    This endpoint is used by the Chrome extension's search feature
    to answer user-submitted questions. It uses the OpenAI API (costs money),
    so authentication is required to prevent abuse.
    
    Returns standardized format:
    {
        "status": "success",
        "status_code": 200,
        "message": "Question answered successfully",
        "result": {...},
        "request_id": "req_abc123",
        "timestamp": "2025-10-18T14:30:00.123Z"
    }
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()

    try:
        start_time = time.time()
        
        logger.info(f"[{request_id}] ❓ Answering question for publisher {publisher.name}: {request.question[:100]}...")
        
        if not request.question or len(request.question.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty"
            )
        
        llm_service = get_llm_service()
        # Generate answer using LLM
        result = await llm_service.answer_question(
            question=request.question,
            context=""  # No context, general Q&A
        )
        
        answer = result.text
        
        # Calculate metadata
        processing_time_ms = (time.time() - start_time) * 1000
        word_count = len(answer.split())
        
        qa_response = QAResponse(
            success=True,
            question=request.question,
            answer=answer,
            word_count=word_count,
            processing_time_ms=processing_time_ms
        )
        
        return success_response(
            result=qa_response.model_dump(),
            message="Question answered successfully",
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
        logger.error(f"[{request_id}] ❌ Q&A failed: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Failed to answer question",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )

