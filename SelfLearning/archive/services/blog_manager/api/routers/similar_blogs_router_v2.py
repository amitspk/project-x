"""
Similar blogs router V2 - Uses Content Processing Service.

Updated to call the consolidated Content Processing Service.
"""

import logging
from fastapi import APIRouter, HTTPException, Request

from ...services.content_service_client import ContentServiceClient
from ...services.cache_service import cache_service
from ...models.request_models import SimilarBlogsRequest
from ...models.response_models import SimilarBlogsResponse
from ...core.config import get_settings
from ...core.rate_limiting import limiter, RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()
content_client = ContentServiceClient(settings)


@router.post(
    "/similar/blogs",
    response_model=SimilarBlogsResponse,
    summary="Find similar blogs",
    description="Find blogs similar to a question using vector search (with caching)"
)
@limiter.limit(RateLimits.SIMILARITY_SEARCH)
async def find_similar_blogs(
    http_request: Request,
    request: SimilarBlogsRequest
):
    """
    Find similar blogs based on a question's semantic meaning.
    
    Uses vector similarity search on blog summary embeddings.
    Results are cached for performance.
    """
    try:
        logger.info(f"🔍 Finding similar blogs for question: {request.question_id}")
        
        # Check cache
        cache_key = cache_service.make_key("similar", request.question_id, str(request.limit))
        cached = await cache_service.get(cache_key)
        
        if cached:
            logger.info(f"✅ Cache hit for similar blogs")
            return cached
        
        # Fetch from Content Service
        result = await content_client.search_similar_blogs(
            question_id=request.question_id,
            limit=request.limit
        )
        
        # Build response
        response = SimilarBlogsResponse(
            question_id=result["question_id"],
            question_text=result["question_text"],
            similar_blogs=result["similar_blogs"]
        )
        
        # Cache result
        await cache_service.set(cache_key, response.dict(), ttl=7200)  # 2 hours
        
        logger.info(f"✅ Found {len(response.similar_blogs)} similar blogs")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Similar blogs search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find similar blogs: {str(e)}"
        )

