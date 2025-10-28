"""
Question generation endpoints for LLM Service.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ...core.service import LLMService
from ...core.interfaces import LLMProvider
from ...services.question_generator import QuestionGenerator
from ..dependencies import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/questions",
    tags=["Questions"],
)


# Request/Response Models
class QuestionGenerationRequest(BaseModel):
    """Request for question generation."""
    content: str = Field(..., description="Content to generate questions from", min_length=10)
    num_questions: Optional[int] = Field(5, description="Number of questions to generate", ge=1, le=20)
    difficulty: Optional[str] = Field("medium", description="Difficulty level (easy/medium/hard)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Python is a high-level programming language...",
                "num_questions": 5,
                "difficulty": "medium"
            }
        }


class Question(BaseModel):
    """A generated question."""
    question: str
    answer: str
    difficulty: str
    category: Optional[str] = None


class QuestionGenerationResponse(BaseModel):
    """Response from question generation."""
    questions: List[Question]
    total_generated: int
    source_word_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "questions": [
                    {
                        "question": "What is Python?",
                        "answer": "A high-level programming language",
                        "difficulty": "easy"
                    }
                ],
                "total_generated": 5,
                "source_word_count": 150
            }
        }


@router.post(
    "/generate",
    response_model=QuestionGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate questions",
    description="Generate questions and answers from content using LLM."
)
async def generate_questions(
    request: QuestionGenerationRequest,
    llm_service: LLMService = Depends(get_llm_service)
) -> QuestionGenerationResponse:
    """Generate questions from content using LLM."""
    try:
        # Simple prompt-based question generation
        prompt = f"""Generate {request.num_questions} questions and answers from the following content.
Difficulty level: {request.difficulty}

Content:
{request.content}

Generate questions in this format:
Q: [question]
A: [answer]

Questions:"""
        
        # Generate using LLM
        response = await llm_service.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=500,
            provider=LLMProvider.OPENAI
        )
        
        # Parse response (simple parsing)
        lines = response.content.strip().split('\n')
        questions_data = []
        current_q = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('Q:'):
                current_q = line[2:].strip()
            elif line.startswith('A:') and current_q:
                answer = line[2:].strip()
                questions_data.append(Question(
                    question=current_q,
                    answer=answer,
                    difficulty=request.difficulty,
                    category=None
                ))
                current_q = None
        
        return QuestionGenerationResponse(
            questions=questions_data[:request.num_questions],
            total_generated=len(questions_data),
            source_word_count=len(request.content.split())
        )
    
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {str(e)}"
        )

