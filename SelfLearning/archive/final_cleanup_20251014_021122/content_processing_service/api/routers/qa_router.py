"""Q&A router - handles custom question answering."""

import logging
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ...services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter()
llm_service = LLMService()


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
    model: Optional[str] = None


@router.post("/ask", response_model=QAResponse)
async def ask_question(request: QARequest):
    """
    Answer a custom question using LLM.
    
    This endpoint is used by the Chrome extension's search feature
    to answer user-submitted questions.
    """
    try:
        start_time = time.time()
        
        logger.info(f"❓ Answering question: {request.question[:100]}...")
        
        if not request.question or len(request.question.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty"
            )
        
        # Generate answer using LLM
        result = await llm_service.answer_question(
            question=request.question,
            context=""  # No context, general Q&A
        )
        
        answer = result.text
        
        # Calculate metadata
        processing_time_ms = (time.time() - start_time) * 1000
        word_count = len(answer.split())
        
        return QAResponse(
            success=True,
            question=request.question,
            answer=answer,
            word_count=word_count,
            processing_time_ms=processing_time_ms,
            model="gpt-4o-mini"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Q&A failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}"
        )

