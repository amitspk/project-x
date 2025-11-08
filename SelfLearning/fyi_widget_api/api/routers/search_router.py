"""Search router - handles similarity search."""

import logging
import sys
import time
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
from fyi_widget_shared_library.utils.url_utils import extract_domain

# Import auth
from fyi_widget_api.api.auth import get_current_publisher, validate_blog_url_domain

# Import metrics
from fyi_widget_api.api.metrics import (
    similarity_searches_total,
    similarity_search_duration_seconds,
    similar_blogs_found,
    question_clicks_total,
    question_click_count
)

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

    # Track metrics
    publisher_domain = publisher.domain.lower()
    search_start_time = time.time()
    
    try:
        logger.info(f"[{request_id}] 🔍 Searching similar blogs for publisher {publisher.name}, question: {request.question_id}")
        
        storage = get_storage()
        # Get the question
        question = await storage.get_question_by_id(request.question_id)
        
        if not question:
            similarity_searches_total.labels(
                publisher_domain=publisher_domain,
                status="error"
            ).inc()
            raise HTTPException(
                status_code=404,
                detail=f"Question not found: {request.question_id}"
            )
        
        # Validate that the question's blog belongs to the publisher
        question_blog_url = question.get("blog_url")
        if not question_blog_url:
            similarity_searches_total.labels(
                publisher_domain=publisher_domain,
                status="error"
            ).inc()
            raise HTTPException(
                status_code=400,
                detail="Question does not have an associated blog URL"
            )
        
        # Validate domain match
        await validate_blog_url_domain(question_blog_url, publisher)
        logger.info(f"[{request_id}] ✅ Question belongs to publisher domain")
        
        # Extract domain from question's blog URL to use for filtering
        question_domain = extract_domain(question_blog_url).lower()
        
        # Track question click (when question is clicked to find similar blogs)
        click_count = await storage.increment_question_click_count(request.question_id)
        if click_count is not None:
            # Record click metrics
            question_clicks_total.labels(
                publisher_domain=publisher_domain,
                blog_url_domain=question_domain
            ).inc()
            
            # Update gauge with current click count
            question_click_count.labels(
                question_id=request.question_id,
                blog_url_domain=question_domain
            ).set(click_count)
            
            logger.info(f"[{request_id}] 👆 Question clicked (count: {click_count})")
        else:
            logger.warning(f"[{request_id}] ⚠️  Could not track click for question {request.question_id}")
        
        # Get embedding
        embedding = question.get("embedding")
        if not embedding:
            similarity_searches_total.labels(
                publisher_domain=publisher_domain,
                status="error"
            ).inc()
            raise HTTPException(
                status_code=400,
                detail="Question does not have an embedding"
            )
        
        # Search for similar blogs (filtered by domain from question's blog at database level)
        similar_blogs = await storage.search_similar_blogs(
            embedding=embedding,
            limit=request.limit,
            publisher_domain=question_domain  # Use domain from question's blog URL
        )
        
        logger.info(f"[{request_id}] 🔍 Found {len(similar_blogs)} similar blogs for domain {question_domain}")
        
        if not similar_blogs:
            logger.warning(f"[{request_id}] ⚠️  No similar blogs found for domain {question_domain}")
        
        # Batch fetch all blogs in a single query
        blog_urls = [blog.url for blog in similar_blogs]
        blogs_map = await storage.get_blogs_by_urls(blog_urls)
        
        # Enrich similar blogs with blog_id
        enriched_blogs = []
        for blog in similar_blogs:
            blog_doc = blogs_map.get(blog.url)
            if blog_doc:
                enriched_blogs.append({
                    "blog_id": str(blog_doc.get("_id", "")),
                    "url": blog.url,
                    "title": blog.title,
                    "similarity_score": blog.similarity_score,
                    "description": None
                })
        
        # Calculate duration and record metrics
        search_duration = time.time() - search_start_time
        
        similarity_searches_total.labels(
            publisher_domain=publisher_domain,
            status="success"
        ).inc()
        
        similarity_search_duration_seconds.labels(
            publisher_domain=publisher_domain
        ).observe(search_duration)
        
        similar_blogs_found.labels(
            publisher_domain=publisher_domain
        ).observe(len(enriched_blogs))
        
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
        # Record error metric
        similarity_searches_total.labels(
            publisher_domain=publisher_domain,
            status="error"
        ).inc()
        
        logger.error(f"[{request_id}] ❌ HTTP error: {exc.detail}")
        response_data = handle_http_exception(exc, request_id=request_id)
        raise HTTPException(
            status_code=response_data["status_code"],
            detail=response_data
        )
    except Exception as e:
        # Record error metric
        similarity_searches_total.labels(
            publisher_domain=publisher_domain,
            status="error"
        ).inc()
        
        # Still record duration even on error
        search_duration = time.time() - search_start_time
        similarity_search_duration_seconds.labels(
            publisher_domain=publisher_domain
        ).observe(search_duration)
        
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

