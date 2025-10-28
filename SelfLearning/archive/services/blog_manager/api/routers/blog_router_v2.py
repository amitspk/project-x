"""
Blog router V2 - Uses Content Processing Service.

This is the updated version that calls the consolidated Content Processing Service
instead of individual microservices.
"""

import logging
from typing import List
from urllib.parse import unquote

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import JSONResponse

from ...services.content_service_client import ContentServiceClient
from ...services.cache_service import cache_service
from ...models.response_models import BlogQuestionsResponse
from ...core.config import get_settings
from ...core.rate_limiting import limiter, RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()
content_client = ContentServiceClient(settings)


@router.get(
    "/blogs/by-url",
    response_model=BlogQuestionsResponse,
    summary="Get blog questions by URL",
    description="Retrieve all questions and answers for a blog (with caching)"
)
@limiter.limit(RateLimits.READ_OPERATIONS)
async def get_blog_questions_by_url(
    request: Request,
    blog_url: str = Query(..., description="Blog URL")
):
    """
    Get questions for a blog URL.
    
    Flow:
    1. Check Redis cache
    2. If not cached, fetch from Content Service
    3. Cache the result
    4. Return questions
    
    **Performance**: Cache hits are ~50-100ms faster!
    """
    try:
        # Decode URL
        decoded_url = unquote(blog_url)
        logger.info(f"📖 Getting questions for: {decoded_url}")
        
        # Check cache first
        cache_key = cache_service.make_key("questions", decoded_url)
        cached = await cache_service.get(cache_key)
        
        if cached:
            logger.info(f"✅ Cache hit for: {decoded_url}")
            return JSONResponse(content=cached)
        
        # Cache miss - fetch from Content Service
        logger.info(f"📡 Fetching from Content Service: {decoded_url}")
        questions = await content_client.get_questions_by_url(decoded_url, limit=20)
        
        if not questions:
            raise HTTPException(
                status_code=404,
                detail=f"No questions found for URL: {decoded_url}"
            )
        
        # Build response
        response_data = {
            "success": True,
            "blog_url": decoded_url,
            "questions": questions,
            "total_questions": len(questions)
        }
        
        # Cache for future requests
        await cache_service.set(cache_key, response_data, ttl=3600)  # 1 hour
        
        logger.info(f"✅ Returned {len(questions)} questions (cached)")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting questions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get questions: {str(e)}"
        )


@router.post(
    "/blogs/process",
    summary="Process a new blog",
    description="Crawl, analyze, and generate questions for a blog URL"
)
@limiter.limit(RateLimits.AI_GENERATION)
async def process_blog(
    request: Request,
    blog_url: str = Query(..., description="Blog URL to process"),
    num_questions: int = Query(default=5, ge=1, le=20),
    force_refresh: bool = Query(default=False)
):
    """
    Process a blog URL through the complete pipeline.
    
    This triggers:
    - Web crawling
    - Content extraction
    - Summary generation (parallel!)
    - Question generation (parallel!)
    - Embeddings generation (parallel!)
    - Database storage
    
    **Optimization**: Parallel LLM operations save ~1500ms!
    """
    try:
        decoded_url = unquote(blog_url)
        logger.info(f"🚀 Processing blog: {decoded_url}")
        
        # Call Content Processing Service
        result = await content_client.process_blog(
            url=decoded_url,
            num_questions=num_questions,
            force_refresh=force_refresh
        )
        
        # Invalidate cache for this URL
        cache_key = cache_service.make_key("questions", decoded_url)
        await cache_service.delete(cache_key)
        
        logger.info(f"✅ Blog processed: {decoded_url} ({result.get('processing_time_ms')}ms)")
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@router.post(
    "/blogs/process-async",
    summary="Process a blog asynchronously",
    description="Start blog processing in background (returns immediately)"
)
@limiter.limit(RateLimits.AI_GENERATION)
async def process_blog_async(
    request: Request,
    blog_url: str = Query(..., description="Blog URL to process"),
    num_questions: int = Query(default=5, ge=1, le=20)
):
    """
    Process a blog asynchronously.
    
    Returns immediately with 202 Accepted.
    Useful for batch processing or user-initiated requests where
    the user doesn't need to wait.
    """
    try:
        decoded_url = unquote(blog_url)
        logger.info(f"🚀 Starting async processing: {decoded_url}")
        
        result = await content_client.process_blog_async(
            url=decoded_url,
            num_questions=num_questions
        )
        
        return JSONResponse(
            content=result,
            status_code=202  # Accepted
        )
        
    except Exception as e:
        logger.error(f"❌ Async processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start processing: {str(e)}"
        )

