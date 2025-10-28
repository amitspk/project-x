"""Search Router - Search and similarity operations."""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ...data.database import db_manager
from ...core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class SimilarityRequest(BaseModel):
    """Similarity search request."""
    embedding: List[float]
    limit: int = 3


class SimilarityResult(BaseModel):
    """Similarity search result."""
    blog_url: str
    title: Optional[str]
    similarity_score: float


@router.post("/similarity", response_model=List[SimilarityResult])
async def similarity_search(request: SimilarityRequest):
    """Perform vector similarity search."""
    try:
        collection = db_manager.get_collection(settings.summary_collection)
        
        # MongoDB Atlas Vector Search (if available)
        # For now, return empty results or implement cosine similarity
        logger.warning("Vector search not fully implemented - returning empty results")
        return []
        
    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blogs")
async def search_blogs(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Number of results")
):
    """Text search for blogs."""
    try:
        collection = db_manager.get_collection(settings.blog_collection)
        
        # Simple text search
        cursor = collection.find(
            {"$text": {"$search": query}}
        ).limit(limit)
        
        docs = await cursor.to_list(length=limit)
        
        return {
            "query": query,
            "results": [
                {
                    "blog_id": doc.get("blog_id", str(doc["_id"])),
                    "url": doc["url"],
                    "title": doc.get("title")
                }
                for doc in docs
            ],
            "count": len(docs)
        }
    except Exception as e:
        logger.error(f"Error searching blogs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

