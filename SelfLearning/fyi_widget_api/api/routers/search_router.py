"""Search router - handles similarity search."""

import logging
import sys
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends

# Add shared to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from fyi_widget_shared_library.services import StorageService
from fyi_widget_shared_library.models.schemas import SearchSimilarRequest, SearchSimilarResponse
from fyi_widget_shared_library.models import SearchResponse as SwaggerSearchResponse, StandardErrorResponse
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

# Storage service will be initialized per-request with database
def get_storage():
    from fyi_widget_api.api.main import db_manager
    return StorageService(database=db_manager.database)


@router.post(
    "/similar",
    response_model=SwaggerSearchResponse,
    responses={
        200: {"description": "Similar blogs found successfully"},
        401: {"model": StandardErrorResponse, "description": "Authentication required - X-API-Key header missing"},
        403: {"model": StandardErrorResponse, "description": "Publisher account not active"},
        404: {"model": StandardErrorResponse, "description": "Question not found"}
    }
)
async def search_similar_blogs(
    http_request: Request,
    request: SearchSimilarRequest,
    publisher: Publisher = Depends(get_current_publisher)
) -> Dict[str, Any]:
    """
    Search for similar blogs based on a question.
    
    **Authentication**: Requires X-API-Key header with valid publisher API key.
    
    This uses the question's embedding to find semantically similar
    blog summaries using vector search. Authentication is required to 
    prevent abuse of the vector database.
    
    Returns standardized format:
    {
        "status": "success",
        "status_code": 200,
        "message": "Similar blogs found successfully",
        "result": {...},
        "request_id": "req_abc123",
        "timestamp": "2025-10-18T14:30:00.123Z"
    }
    """
    # Get request_id from middleware (fallback to generating one if not available)
    request_id = getattr(http_request.state, 'request_id', None) or generate_request_id()

    try:
        logger.info(f"[{request_id}] 🔍 Searching similar blogs for publisher {publisher.name}, question: {request.question_id}")
        
        storage = get_storage()
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
        
        # Enrich similar blogs with blog_id
        enriched_blogs = []
        for blog in similar_blogs:
            # Get blog document to fetch blog_id
            blog_doc = await storage.get_blog_by_url(blog.url)
            if blog_doc:
                enriched_blogs.append({
                    "blog_id": str(blog_doc.get("_id", "")),
                    "url": blog.url,
                    "title": blog.title,
                    "similarity_score": blog.similarity_score,
                    "icon": "❓",
                    "description": None
                })
        
        # Build response in the format expected by Swagger schema
        result_data = {
            "similar_blogs": enriched_blogs,
            "total": len(enriched_blogs)
        }
        
        return success_response(
            result=result_data,
            message=f"Found {len(enriched_blogs)} similar blogs",
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
        logger.error(f"[{request_id}] ❌ Similarity search failed: {e}", exc_info=True)
        response_data = handle_generic_exception(
            e,
            message="Similarity search failed",
            request_id=request_id
        )
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )

