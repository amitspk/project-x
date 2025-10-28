"""Search router - handles similarity search."""

import logging
from fastapi import APIRouter, HTTPException
from ...models.schemas import SearchSimilarRequest, SearchSimilarResponse
from ...services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter()
storage = StorageService()


@router.post("/similar", response_model=SearchSimilarResponse)
async def search_similar_blogs(request: SearchSimilarRequest):
    """
    Search for similar blogs based on a question.
    
    This uses the question's embedding to find semantically similar
    blog summaries using vector search.
    """
    try:
        logger.info(f"🔍 Searching similar blogs for question: {request.question_id}")
        
        # Get the question
        question = await storage.get_question_by_id(request.question_id)
        
        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question not found: {request.question_id}"
            )
        
        # Get embedding
        embedding = question.get("embedding")
        if not embedding:
            raise HTTPException(
                status_code=400,
                detail="Question does not have an embedding"
            )
        
        # Search for similar blogs
        similar_blogs = await storage.search_similar_blogs(
            embedding=embedding,
            limit=request.limit
        )
        
        return SearchSimilarResponse(
            question_id=request.question_id,
            question_text=question.get("question", ""),
            similar_blogs=similar_blogs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Similarity search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

