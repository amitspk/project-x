"""
Blog router for the blog manager microservice.

Provides REST API endpoints for blog-related operations.
"""

import logging
from typing import Optional, List
from urllib.parse import unquote

from fastapi import APIRouter, Query, HTTPException, Path, Request
from fastapi.responses import JSONResponse

from ...services.blog_service import BlogService
from ...models.request_models import BlogUrlRequest, BlogLookupRequest
from ...models.response_models import BlogQuestionsResponse, BlogInfoModel, ErrorResponse
from ...core.exceptions import (
    BlogNotFoundException,
    NoQuestionsFoundException,
    InvalidUrlException,
    ValidationException
)
from ...core.rate_limiting import limiter, RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()
blog_service = BlogService()


@router.get(
    "/blogs/by-url",
    response_model=BlogQuestionsResponse,
    summary="Get blog questions by URL",
    description="Retrieve all questions and answers for a blog identified by its URL",
    responses={
        200: {
            "description": "Successfully retrieved blog questions",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "blog_info": {
                            "blog_id": "effective_use_of_threadlocal_in_java_app_5bbb34ce",
                            "title": "Effective Use of ThreadLocal in Java Applications",
                            "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
                            "author": "Alex Klimenko",
                            "word_count": 3659,
                            "source_domain": "medium.com"
                        },
                        "questions": [
                            {
                                "id": "q1",
                                "question": "What are the potential risks of not using ThreadLocal?",
                                "answer": "Not using ThreadLocal can lead to data inconsistency...",
                                "question_type": "cause and effect",
                                "difficulty_level": "intermediate",
                                "question_order": 1,
                                "confidence_score": 0.9
                            }
                        ],
                        "total_questions": 10,
                        "returned_questions": 10,
                        "has_more": False,
                        "processing_time_ms": 45.2
                    }
                }
            }
        },
        404: {
            "description": "Blog not found or no questions available",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "BLOG_NOT_FOUND",
                        "message": "Blog not found for URL: https://example.com/nonexistent",
                        "timestamp": "2025-10-02T20:52:42.869Z"
                    }
                }
            }
        },
        400: {
            "description": "Invalid URL format",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "INVALID_URL",
                        "message": "Invalid URL format: invalid-url",
                        "timestamp": "2025-10-02T20:52:42.869Z"
                    }
                }
            }
        }
    },
    tags=["Blogs"]
)
@limiter.limit(RateLimits.READ_OPERATIONS)  # 100 requests per minute for read operations
async def get_blog_questions_by_url(
    request: Request,
    url: str = Query(
        ...,
        description="The blog URL to lookup",
        example="https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
    ),
    include_summary: bool = Query(
        default=False,
        description="Whether to include blog summary in response"
    ),
    include_metadata: bool = Query(
        default=True,
        description="Whether to include question metadata"
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=100,
        description="Maximum number of questions to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of questions to skip (for pagination)"
    )
):
    """
    Get blog questions by URL.
    
    This is the main endpoint for retrieving questions and answers for a blog
    when you have the blog's URL. The service will:
    
    1. Validate the URL format
    2. Look up the blog in the database
    3. Retrieve all associated questions and answers
    4. Return formatted response with metadata
    
    **Example Usage:**
    ```
    GET /api/v1/blogs/by-url?url=https://medium.com/@author/article-title
    ```
    
    **Response includes:**
    - Blog information (title, author, URL, etc.)
    - List of questions and answers
    - Optional summary (if include_summary=true)
    - Metadata (total questions, confidence scores, etc.)
    """
    try:
        # URL decode in case it's encoded
        decoded_url = unquote(url)
        
        logger.info(f"Getting blog questions for URL: {decoded_url}")
        
        result = await blog_service.get_blog_questions_by_url(
            url=decoded_url,
            include_summary=include_summary,
            include_metadata=include_metadata,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Successfully retrieved {result.returned_questions} questions for blog: {result.blog_info.title}")
        
        return result
        
    except BlogNotFoundException as e:
        logger.warning(f"Blog not found for URL: {decoded_url}")
        raise HTTPException(status_code=404, detail=e.message)
    
    except NoQuestionsFoundException as e:
        logger.warning(f"No questions found for blog: {e.details.get('blog_id')}")
        raise HTTPException(status_code=404, detail=e.message)
    
    except InvalidUrlException as e:
        logger.warning(f"Invalid URL provided: {decoded_url}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error getting blog questions by URL: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/blogs/{blog_id}/questions",
    response_model=BlogQuestionsResponse,
    summary="Get blog questions by ID",
    description="Retrieve all questions and answers for a blog identified by its internal blog_id",
    responses={
        200: {
            "description": "Successfully retrieved blog questions",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "blog_info": {
                            "blog_id": "effective_use_of_threadlocal_in_java_app_5bbb34ce",
                            "title": "Effective Use of ThreadLocal in Java Applications",
                            "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
                        },
                        "questions": [
                            {
                                "id": "q1",
                                "question": "What are the potential risks of not using ThreadLocal?",
                                "answer": "Not using ThreadLocal can lead to data inconsistency...",
                                "question_type": "cause and effect",
                                "question_order": 1,
                                "confidence_score": 0.9
                            }
                        ],
                        "total_questions": 10,
                        "returned_questions": 3,
                        "has_more": True
                    }
                }
            }
        },
        404: {
            "description": "Blog not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "BLOG_NOT_FOUND",
                        "message": "Blog not found for blog_id: nonexistent_id",
                        "timestamp": "2025-10-02T20:52:42.869Z"
                    }
                }
            }
        }
    },
    tags=["Blogs"]
)
async def get_blog_questions_by_id(
    blog_id: str = Path(
        ...,
        description="The internal blog identifier",
        example="effective_use_of_threadlocal_in_java_app_5bbb34ce"
    ),
    include_summary: bool = Query(
        default=False,
        description="Whether to include blog summary in response"
    ),
    include_metadata: bool = Query(
        default=True,
        description="Whether to include question metadata"
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=100,
        description="Maximum number of questions to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of questions to skip (for pagination)"
    )
):
    """
    Get blog questions by internal blog ID.
    
    Use this endpoint when you already know the internal blog_id.
    This is typically faster than URL lookup as it's a direct database query.
    
    **Example Usage:**
    ```
    GET /api/v1/blogs/effective_use_of_threadlocal_in_java_app_5bbb34ce/questions
    ```
    """
    try:
        logger.info(f"Getting blog questions for blog_id: {blog_id}")
        
        result = await blog_service.get_blog_questions_by_id(
            blog_id=blog_id,
            include_summary=include_summary,
            include_metadata=include_metadata,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Successfully retrieved {result.returned_questions} questions for blog_id: {blog_id}")
        
        return result
        
    except BlogNotFoundException as e:
        logger.warning(f"Blog not found for blog_id: {blog_id}")
        raise HTTPException(status_code=404, detail=e.message)
    
    except NoQuestionsFoundException as e:
        logger.warning(f"No questions found for blog_id: {blog_id}")
        raise HTTPException(status_code=404, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error getting blog questions by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/blogs/search",
    response_model=List[BlogInfoModel],
    summary="Search blogs",
    description="Search for blogs by text query using full-text search capabilities",
    responses={
        200: {
            "description": "Successfully found matching blogs",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "blog_id": "effective_use_of_threadlocal_in_java_app_5bbb34ce",
                            "title": "Effective Use of ThreadLocal in Java Applications",
                            "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
                            "author": "Alex Klimenko",
                            "word_count": 3659,
                            "source_domain": "medium.com"
                        }
                    ]
                }
            }
        }
    },
    tags=["Blogs"]
)
async def search_blogs(
    q: str = Query(
        ...,
        description="Search query",
        example="ThreadLocal Java concurrency"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of results to skip (for pagination)"
    )
):
    """
    Search for blogs by text query.
    
    Performs full-text search across blog titles and content to find relevant blogs.
    
    **Example Usage:**
    ```
    GET /api/v1/blogs/search?q=ThreadLocal Java&limit=5
    ```
    """
    try:
        logger.info(f"Searching blogs with query: {q}")
        
        results = await blog_service.search_blogs(
            query=q,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Found {len(results)} blogs for query: {q}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching blogs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/blogs/recent",
    response_model=List[BlogInfoModel],
    summary="Get recent blogs",
    description="Get recently added blogs ordered by creation date",
    responses={
        200: {
            "description": "Successfully retrieved recent blogs",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "blog_id": "effective_use_of_threadlocal_in_java_app_5bbb34ce",
                            "title": "Effective Use of ThreadLocal in Java Applications",
                            "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
                            "author": "Alex Klimenko",
                            "word_count": 3659,
                            "source_domain": "medium.com"
                        }
                    ]
                }
            }
        }
    },
    tags=["Blogs"]
)
async def get_recent_blogs(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of blogs to return"
    )
):
    """
    Get recently added blogs.
    
    Returns the most recently processed blogs, ordered by creation date.
    
    **Example Usage:**
    ```
    GET /api/v1/blogs/recent?limit=5
    ```
    """
    try:
        logger.info(f"Getting {limit} recent blogs")
        
        results = await blog_service.get_recent_blogs(limit=limit)
        
        logger.info(f"Retrieved {len(results)} recent blogs")
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting recent blogs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/blogs/stats",
    summary="Get blog statistics",
    description="Get overall statistics about blogs and questions in the system",
    responses={
        200: {
            "description": "Successfully retrieved blog statistics",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "statistics": {
                            "total_blogs": 156,
                            "total_questions": 1560,
                            "recent_blogs_available": True,
                            "last_updated": "2025-10-02T20:52:42.869Z"
                        },
                        "timestamp": "2025-10-02T20:52:42.869Z"
                    }
                }
            }
        }
    },
    tags=["Blogs"]
)
async def get_blog_statistics():
    """
    Get blog statistics.
    
    Returns overall statistics about the blogs and questions in the system.
    
    **Example Usage:**
    ```
    GET /api/v1/blogs/stats
    ```
    """
    try:
        logger.info("Getting blog statistics")
        
        stats = await blog_service.get_blog_statistics()
        
        logger.info("Successfully retrieved blog statistics")
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": "2025-10-02T20:52:42.869Z"  # This would be dynamic
        }
        
    except Exception as e:
        logger.error(f"Error getting blog statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
