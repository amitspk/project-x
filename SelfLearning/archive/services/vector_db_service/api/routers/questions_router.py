"""Questions Router - Question operations."""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ...data.database import db_manager
from ...core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class QuestionResponse(BaseModel):
    """Question response model."""
    question_id: str
    blog_url: str
    question: str
    answer: str
    category: Optional[str] = None
    difficulty: Optional[str] = None


@router.get("/by-url", response_model=List[QuestionResponse])
async def get_questions_by_url(url: str = Query(..., description="Blog URL")):
    """Get questions for a blog URL."""
    try:
        collection = db_manager.get_collection(settings.question_collection)
        cursor = collection.find({"blog_url": url})
        docs = await cursor.to_list(length=100)
        
        if not docs:
            return []
        
        return [
            QuestionResponse(
                question_id=str(doc["_id"]),
                blog_url=doc["blog_url"],
                question=doc["question"],
                answer=doc["answer"],
                category=doc.get("category"),
                difficulty=doc.get("difficulty")
            )
            for doc in docs
        ]
    except Exception as e:
        logger.error(f"Error fetching questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question_by_id(question_id: str):
    """Get a specific question by ID."""
    try:
        from bson import ObjectId
        
        collection = db_manager.get_collection(settings.question_collection)
        doc = await collection.find_one({"_id": ObjectId(question_id)})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Question not found")
        
        return QuestionResponse(
            question_id=str(doc["_id"]),
            blog_url=doc["blog_url"],
            question=doc["question"],
            answer=doc["answer"],
            category=doc.get("category"),
            difficulty=doc.get("difficulty")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

