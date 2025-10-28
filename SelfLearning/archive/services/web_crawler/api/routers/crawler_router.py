"""
Crawler API Router.

Provides endpoints for web crawling operations.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, HttpUrl

from ...core.crawler import WebCrawler
from ...utils.exceptions import CrawlerError, NetworkError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class CrawlRequest(BaseModel):
    """Request model for crawling a URL."""
    url: str = Field(..., description="URL to crawl", example="https://example.com")
    extract_text: bool = Field(True, description="Extract and clean text content")
    save_to_file: bool = Field(True, description="Save crawled content to file")
    follow_redirects: bool = Field(True, description="Follow HTTP redirects")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://blog.example.com/article",
                "extract_text": True,
                "save_to_file": True,
                "follow_redirects": True
            }
        }


class CrawlResponse(BaseModel):
    """Response model for crawl operation."""
    url: str = Field(..., description="Crawled URL")
    status: str = Field(..., description="Crawl status")
    title: Optional[str] = Field(None, description="Page title")
    content: Optional[str] = Field(None, description="Extracted text content")
    word_count: Optional[int] = Field(None, description="Number of words in content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    saved_to: Optional[str] = Field(None, description="File path if saved")
    crawled_at: str = Field(..., description="Timestamp of crawl")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://blog.example.com/article",
                "status": "success",
                "title": "Understanding Microservices",
                "content": "Microservices are...",
                "word_count": 500,
                "metadata": {
                    "domain": "blog.example.com",
                    "content_type": "text/html"
                },
                "saved_to": "crawled_content/blog.example.com/article.txt",
                "crawled_at": "2025-10-13T22:00:00Z"
            }
        }


class ConfigResponse(BaseModel):
    """Response model for crawler configuration."""
    timeout: int
    max_retries: int
    delay_between_requests: float
    requests_per_minute: int
    max_content_size: int
    user_agent: str
    verify_ssl: bool
    output_directory: str


class StatusResponse(BaseModel):
    """Response model for crawler status."""
    service: str
    status: str
    config: ConfigResponse
    stats: Dict[str, Any]


# Dependency injection
def get_crawler_dep() -> WebCrawler:
    """Dependency to get crawler instance."""
    from ..main import get_crawler
    return get_crawler()


# Endpoints
@router.post(
    "/crawl",
    response_model=CrawlResponse,
    status_code=status.HTTP_200_OK,
    summary="Crawl a web page",
    description="Crawl a URL and extract content with optional text cleaning and file storage."
)
async def crawl_url(
    request: CrawlRequest,
    crawler: WebCrawler = Depends(get_crawler_dep)
) -> CrawlResponse:
    """
    Crawl a web page and return structured data.
    
    - **url**: The URL to crawl (required)
    - **extract_text**: Extract and clean text content (default: true)
    - **save_to_file**: Save content to file (default: true)
    - **follow_redirects**: Follow HTTP redirects (default: true)
    """
    try:
        logger.info(f"Crawling URL: {request.url}")
        
        # Perform crawl
        result = await crawler.crawl(request.url)
        
        # Extract text if requested
        content = None
        word_count = None
        if request.extract_text and 'content' in result:
            content = result['content']
            word_count = len(content.split()) if content else 0
        
        # Build response
        response = CrawlResponse(
            url=result.get('url', request.url),
            status="success",
            title=result.get('title'),
            content=content if request.extract_text else None,
            word_count=word_count,
            metadata={
                "domain": result.get('domain'),
                "content_type": result.get('content_type'),
                "status_code": result.get('status_code'),
                "response_time": result.get('fetch_time'),
                "final_url": result.get('final_url')
            },
            saved_to=result.get('file_path') if request.save_to_file else None,
            crawled_at=datetime.utcnow().isoformat() + "Z"
        )
        
        logger.info(f"Successfully crawled: {request.url} ({word_count} words)")
        return response
        
    except CrawlerError as e:
        logger.error(f"Crawler error for {request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Crawling failed: {str(e)}"
        )
    except NetworkError as e:
        logger.error(f"Network error for {request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error crawling {request.url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.get(
    "/status",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get crawler status",
    description="Get current crawler configuration and statistics."
)
async def get_status(
    crawler: WebCrawler = Depends(get_crawler_dep)
) -> StatusResponse:
    """Get crawler service status and configuration."""
    try:
        config = crawler.config
        
        return StatusResponse(
            service="web-crawler-service",
            status="operational",
            config=ConfigResponse(
                timeout=config.timeout,
                max_retries=config.max_retries,
                delay_between_requests=config.delay_between_requests,
                requests_per_minute=config.requests_per_minute,
                max_content_size=config.max_content_size,
                user_agent=config.user_agent,
                verify_ssl=config.verify_ssl,
                output_directory=str(config.output_directory)
            ),
            stats={
                "session_active": crawler._session is not None,
                "rate_limit_requests": len(crawler._request_times)
            }
        )
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get(
    "/config",
    response_model=ConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get crawler configuration",
    description="Get current crawler configuration settings."
)
async def get_config(
    crawler: WebCrawler = Depends(get_crawler_dep)
) -> ConfigResponse:
    """Get crawler configuration."""
    try:
        config = crawler.config
        
        return ConfigResponse(
            timeout=config.timeout,
            max_retries=config.max_retries,
            delay_between_requests=config.delay_between_requests,
            requests_per_minute=config.requests_per_minute,
            max_content_size=config.max_content_size,
            user_agent=config.user_agent,
            verify_ssl=config.verify_ssl,
            output_directory=str(config.output_directory)
        )
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get config: {str(e)}"
        )

