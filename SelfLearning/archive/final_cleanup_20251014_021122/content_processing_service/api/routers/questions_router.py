"""Questions router - handles question retrieval."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from ...models.schemas import QuestionAnswerPair
from ...services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter()
storage = StorageService()


@router.get("/by-url")
async def get_questions_by_url(
    blog_url: str = Query(..., description="Blog URL"),
    limit: int = Query(default=10, ge=1, le=50, description="Max questions to return")
) -> Dict[str, Any]:
    """
    Get all questions for a specific blog URL.
    
    Returns format expected by Chrome extension:
    {
        "success": true,
        "questions": [...],
        "blog_info": {...}
    }
    """
    try:
        logger.info(f"📖 Getting questions for: {blog_url}")
        
        questions = await storage.get_questions_by_url(blog_url, limit)
        
        if not questions:
            raise HTTPException(
                status_code=404,
                detail=f"No questions found for URL: {blog_url}"
            )
        
        # Get blog metadata
        blog_info = await storage.get_blog_by_url(blog_url)
        
        # Format response for Chrome extension
        return {
            "success": True,
            "questions": questions,
            "blog_info": {
                "title": blog_info.get("title", "") if blog_info else "",
                "url": blog_url,
                "author": blog_info.get("author", "") if blog_info else "",
                "published_date": blog_info.get("published_date", "") if blog_info else "",
                "question_count": len(questions)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get questions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve questions: {str(e)}"
        )


@router.get("/{question_id}")
async def get_question_by_id(question_id: str):
    """Get a specific question by ID."""
    try:
        question = await storage.get_question_by_id(question_id)
        
        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question not found: {question_id}"
            )
        
        # Convert ObjectId to string
        question["_id"] = str(question["_id"])
        
        return question
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get question: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve question: {str(e)}"
        )

