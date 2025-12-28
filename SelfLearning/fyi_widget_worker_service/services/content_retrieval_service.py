"""Service for retrieving and caching blog content."""

import logging
import time
from typing import Optional

from fyi_widget_worker_service.models.schema_models import CrawledContent
from fyi_widget_worker_service.services.blog_crawler import BlogCrawler
from fyi_widget_worker_service.services.blog_content_repository import BlogContentRepository
from fyi_widget_worker_service.utils import normalize_url

from fyi_widget_worker_service.core.metrics import (
    crawl_operations_total,
    crawl_duration_seconds,
    crawl_content_size_bytes,
    crawl_word_count,
    db_operations_total,
    db_operation_duration_seconds,
    processing_errors_total,
)

logger = logging.getLogger(__name__)


class ContentRetrievalService:
    """Service for retrieving blog content (from cache or by crawling)."""
    
    def __init__(
        self,
        crawler: BlogCrawler,
        storage: BlogContentRepository,
    ):
        """
        Initialize content retrieval service.
        
        Args:
            crawler: BlogCrawler instance
            storage: BlogContentRepository instance
        """
        self.crawler = crawler
        self.storage = storage
    
    async def get_blog_content(
        self,
        url: str,
        publisher_domain: str,
    ) -> tuple[Optional[CrawledContent], Optional[str], Optional[dict]]:
        """
        Get blog content, either from cache or by crawling.
        
        Args:
            url: Blog URL to retrieve
            publisher_domain: Publisher domain for metrics
            
        Returns:
            Tuple of (CrawledContent, blog_id, blog_doc)
            - CrawledContent: The crawled/extracted content
            - blog_id: The MongoDB document ID (None if not saved)
            - blog_doc: The raw blog document from DB (for threshold checks)
            
        Raises:
            Exception: If content retrieval fails
        """
        normalized_url = normalize_url(url)
        logger.info(f"🔍 Checking for existing raw content: {normalized_url}")
        
        crawl_start = time.time()
        crawl_result = None
        blog_id = None
        blog_doc = None
        
        # First, check if raw content already exists in database
        existing_blog = await self.storage.get_blog_by_url(normalized_url)
        
        if existing_blog:
            # Store blog document for later use (threshold check)
            blog_doc = existing_blog
            
            # Convert existing blog to CrawledContent format
            blog_id = str(existing_blog["_id"])
            crawl_result = CrawledContent(
                url=normalized_url,
                title=existing_blog.get("title", ""),
                content=existing_blog.get("content", ""),
                language=existing_blog.get("language", "en"),
                word_count=existing_blog.get("word_count", 0),
                metadata=existing_blog.get("metadata", {})
            )
            
            # Validate existing content
            if not crawl_result.content or len(crawl_result.content.strip()) < 50:
                logger.warning(f"⚠️  Existing content is invalid, will re-crawl: {normalized_url}")
                crawl_result = None  # Force re-crawl
                blog_doc = None  # Clear blog_doc since we'll re-crawl
            else:
                crawl_duration = time.time() - crawl_start
                crawl_operations_total.labels(publisher_domain=publisher_domain, status="cached").inc()
                crawl_duration_seconds.labels(publisher_domain=publisher_domain).observe(crawl_duration)
                crawl_content_size_bytes.labels(publisher_domain=publisher_domain).observe(len(crawl_result.content.encode('utf-8')))
                crawl_word_count.labels(publisher_domain=publisher_domain).observe(crawl_result.word_count)
                
                logger.info(f"✅ Using existing raw content: {crawl_result.word_count} words (blog_id: {blog_id})")
                return crawl_result, blog_id, blog_doc
        
        # If no existing content or invalid, crawl the blog
        if crawl_result is None:
            logger.info(f"🕷️  Crawling: {normalized_url}")
            try:
                crawl_result = await self.crawler.crawl_url(normalized_url)
                
                # crawl_result is CrawledContent on success, exception raised on failure
                if not crawl_result or not crawl_result.content:
                    raise Exception("Crawl failed: No content extracted")
                
                # Additional validation: check content quality
                if len(crawl_result.content.strip()) < 50:
                    raise Exception(f"Crawl failed: Content too short ({len(crawl_result.content)} chars)")
                
                # Record crawl metrics
                crawl_duration = time.time() - crawl_start
                crawl_operations_total.labels(publisher_domain=publisher_domain, status="success").inc()
                crawl_duration_seconds.labels(publisher_domain=publisher_domain).observe(crawl_duration)
                crawl_content_size_bytes.labels(publisher_domain=publisher_domain).observe(len(crawl_result.content.encode('utf-8')))
                crawl_word_count.labels(publisher_domain=publisher_domain).observe(crawl_result.word_count)
                
                logger.info(f"✅ Crawl successful: {crawl_result.word_count} words extracted")
                
                # Save raw blog content immediately after crawl succeeds
                # This ensures content is preserved even if later processing steps fail
                logger.info("💾 Saving raw blog content...")
                db_start = time.time()
                try:
                    blog_id = await self.storage.save_blog_content(
                        url=normalized_url,
                        title=crawl_result.title,  # Will be updated later if LLM generates a better title
                        content=crawl_result.content,
                        language=crawl_result.language,
                        word_count=crawl_result.word_count,
                        metadata=crawl_result.metadata
                    )
                    db_duration = time.time() - db_start
                    db_operations_total.labels(operation="save_blog", collection="raw_blog_content", status="success").inc()
                    db_operation_duration_seconds.labels(operation="save_blog", collection="raw_blog_content").observe(db_duration)
                    logger.info(f"✅ Raw blog content saved: {blog_id}")
                    
                    # Get the saved blog document for threshold check (single call)
                    blog_doc = await self.storage.get_blog_by_url(normalized_url)
                    if not blog_doc:
                        raise Exception("Blog document not found after save")
                except Exception as save_error:
                    db_duration = time.time() - db_start
                    db_operations_total.labels(operation="save_blog", collection="raw_blog_content", status="error").inc()
                    db_operation_duration_seconds.labels(operation="save_blog", collection="raw_blog_content").observe(db_duration)
                    # Log but don't fail - we can try again later or the content might already exist
                    logger.warning(f"⚠️  Failed to save raw blog content: {save_error}. Continuing with processing...")
                    blog_id = None
                    blog_doc = None
                
            except Exception as crawl_error:
                # Record crawl failure
                crawl_duration = time.time() - crawl_start
                crawl_operations_total.labels(publisher_domain=publisher_domain, status="failed").inc()
                crawl_duration_seconds.labels(publisher_domain=publisher_domain).observe(crawl_duration)
                processing_errors_total.labels(publisher_domain=publisher_domain, error_type="crawl_error").inc()
                logger.error(f"❌ Crawl failed for {normalized_url}: {crawl_error}")
                raise Exception(f"Crawl failed: {str(crawl_error)}")
        
        # Ensure blog_id and blog_doc are available
        if blog_id is None or blog_doc is None:
            # Fallback: Try to get blog from database
            fallback_blog = await self.storage.get_blog_by_url(normalized_url)
            if fallback_blog:
                blog_id = str(fallback_blog["_id"])
                blog_doc = fallback_blog
            else:
                raise Exception("Blog ID and document not available after crawl/save")
        
        return crawl_result, blog_id, blog_doc

