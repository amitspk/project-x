"""
Q&A endpoints for LLM Service.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ...core.service import LLMService
from ...core.interfaces import LLMProvider
from ..dependencies import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/qa",
    tags=["Q&A"],
)


# Request/Response Models
class QARequest(BaseModel):
    """Request for Q&A generation."""
    question: str = Field(..., description="Question to answer", min_length=1)
    context: Optional[str] = Field(None, description="Optional context for the question")
    max_words: Optional[int] = Field(200, description="Maximum words in answer", ge=10, le=1000)
    temperature: Optional[float] = Field(0.7, description="Sampling temperature", ge=0.0, le=2.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is Python?",
                "max_words": 200,
                "temperature": 0.7
            }
        }


class QAResponse(BaseModel):
    """Response from Q&A generation."""
    question: str
    answer: str
    word_count: int
    model: str
    provider: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is Python?",
                "answer": "Python is a high-level programming language...",
                "word_count": 45,
                "model": "gpt-4",
                "provider": "openai"
            }
        }


@router.post(
    "/answer",
    response_model=QAResponse,
    status_code=status.HTTP_200_OK,
    summary="Answer a question",
    description="Generate an answer to a question using LLM."
)
async def answer_question(
    request: QARequest,
    llm_service: LLMService = Depends(get_llm_service)
) -> QAResponse:
    """Answer a question using LLM."""
    try:
        # Build prompt
        if request.context:
            prompt = f"""Context: {request.context}

Question: {request.question}

Please provide a clear, accurate, and concise answer (approximately {request.max_words} words or less).

Answer:"""
        else:
            prompt = f"""Question: {request.question}

Please provide a clear, accurate, and concise answer (approximately {request.max_words} words or less).

Answer:"""
        
        # Generate answer
        max_tokens = int(request.max_words * 1.5)  # Rough estimate
        response = await llm_service.generate(
            prompt=prompt,
            temperature=request.temperature,
            max_tokens=max_tokens,
            provider=LLMProvider.OPENAI
        )
        
        answer = response.content.strip()
        word_count = len(answer.split())
        
        return QAResponse(
            question=request.question,
            answer=answer,
            word_count=word_count,
            model=response.model,
            provider=response.provider if isinstance(response.provider, str) else response.provider.value
        )
    
    except Exception as e:
        logger.error(f"Q&A generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Q&A generation failed: {str(e)}"
        )

