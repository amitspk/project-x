"""
Main web crawler implementation with production-grade features.

Provides robust web crawling with rate limiting, error handling,
retry mechanisms, and proper resource management.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from urllib.parse import urljoin, urlparse
from ..core.interfaces import ICrawler, IContentExtractor, IStorage
from ..core.extractor import ContentExtractor
from ..storage.file_handler import FileStorage
from ..utils.validators import URLValidator
from ..utils.exceptions import CrawlerError, NetworkError, RateLimitError
from ..config.settings import CrawlerConfig

logger = logging.getLogger(__name__)


class WebCrawler(ICrawler):
    """Production-grade web crawler with comprehensive features."""
    
    def __init__(self, 
                 config: Optional[CrawlerConfig] = None,
                 content_extractor: Optional[IContentExtractor] = None,
                 storage: Optional[IStorage] = None):
        """
        Initialize web crawler.
        
        Args:
            config: Crawler configuration
            content_extractor: Content extraction implementation
            storage: Storage implementation
        """
        self.config = config or CrawlerConfig()
        self.content_extractor = content_extractor or ContentExtractor()
        self.storage = storage or FileStorage(self.config.output_directory)
        
        # Rate limiting
        self._request_times = []
        self._rate_limit_lock = asyncio.Lock()
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
    
    async def crawl(self, url: str) -> Dict[str, Any]:
        """
        Crawl a web page and return structured data.
        
        Args:
            url: The URL to crawl
            
        Returns:
            Dictionary containing crawled data
            
        Raises:
            CrawlerError: If crawling fails
        """
        # Validate URL
        try:
            parsed_url = URLValidator.validate_url(url, self.config.allow_local_urls)
        except Exception as e:
            raise CrawlerError(f"URL validation failed: {e}", url)
        
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Perform crawl with retries
        for attempt in range(self.config.max_retries + 1):
            try:
                return await self._perform_crawl(url, parsed_url)
                
            except (NetworkError, aiohttp.ClientError) as e:
                if attempt == self.config.max_retries:
                    raise CrawlerError(f"Max retries exceeded: {e}", url)
                
                # Exponential backoff
                wait_time = min(2 ** attempt, 30)
                logger.warning(f"Crawl attempt {attempt + 1} failed for {url}, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            
            except Exception as e:
                logger.error(f"Unexpected error crawling {url}: {e}")
                raise CrawlerError(f"Crawl failed: {e}", url)
    
    async def crawl_and_save(self, url: str) -> Dict[str, Any]:
        """
        Crawl a URL and save content to file.
        
        Args:
            url: URL to crawl
            
        Returns:
            Dictionary with crawl results and file path
        """
        # Crawl the URL
        crawl_result = await self.crawl(url)
        
        # Generate filename
        filename = URLValidator.sanitize_filename(url)
        
        # Prepare content for saving
        content_parts = []
        
        # Add metadata header
        if crawl_result.get('metadata'):
            from ..utils.text_processor import TextProcessor
            metadata_text = TextProcessor.format_metadata(crawl_result['metadata'])
            content_parts.append(metadata_text)
            content_parts.append('\n\n')
        
        # Add main content
        if crawl_result.get('content'):
            content_parts.append(crawl_result['content'])
        
        content_to_save = ''.join(content_parts)
        
        # Save to file
        try:
            file_path = await self.storage.save_content(
                content=content_to_save,
                filename=filename,
                metadata={
                    **crawl_result.get('metadata', {}),
                    'source_url': url,
                    'crawled_at': datetime.utcnow().isoformat(),
                    'content_length': len(content_to_save)
                }
            )
            
            crawl_result['saved_to'] = str(file_path)
            logger.info(f"Successfully crawled and saved {url} to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save content for {url}: {e}")
            crawl_result['save_error'] = str(e)
        
        return crawl_result
    
    async def _perform_crawl(self, url: str, parsed_url) -> Dict[str, Any]:
        """
        Perform the actual crawling operation.
        
        Args:
            url: URL to crawl
            parsed_url: Parsed URL object
            
        Returns:
            Crawl results dictionary
        """
        session = await self._get_session()
        
        try:
            # Make HTTP request
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                allow_redirects=self.config.follow_redirects,
                max_redirects=self.config.max_redirects
            ) as response:
                
                # Check response status
                if response.status >= 400:
                    raise NetworkError(f"HTTP {response.status}: {response.reason}", url, response.status)
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if not any(allowed in content_type for allowed in self.config.allowed_content_types):
                    raise CrawlerError(f"Unsupported content type: {content_type}", url)
                
                # Check content size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.config.max_content_size:
                    raise CrawlerError(f"Content too large: {content_length} bytes", url)
                
                # Read content with size limit
                content = await self._read_content_with_limit(response)
                
                # Extract text and metadata
                text_content = self.content_extractor.extract_text(content)
                metadata = self.content_extractor.extract_metadata(content)
                
                # Extract structured content for detailed analysis
                structured_content = self.content_extractor.extract_structured_content(content)
                
                # Prepare result
                result = {
                    'url': url,
                    'final_url': str(response.url),
                    'status_code': response.status,
                    'content_type': content_type,
                    'content_length': len(content),
                    'text_length': len(text_content),
                    'content': text_content,
                    'metadata': metadata,
                    'structured_content': structured_content,
                    'headers': dict(response.headers),
                    'crawled_at': datetime.utcnow().isoformat()
                }
                
                logger.info(f"Successfully crawled {url} ({len(text_content)} chars)")
                return result
                
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error: {e}", url)
        except asyncio.TimeoutError:
            raise NetworkError("Request timeout", url)
    
    async def _read_content_with_limit(self, response: aiohttp.ClientResponse) -> str:
        """
        Read response content with size limit protection.
        
        Args:
            response: HTTP response object
            
        Returns:
            Response content as string
        """
        content_bytes = b''
        bytes_read = 0
        
        async for chunk in response.content.iter_chunked(8192):
            bytes_read += len(chunk)
            if bytes_read > self.config.max_content_size:
                raise CrawlerError(f"Content exceeds size limit: {bytes_read} bytes")
            content_bytes += chunk
        
        # Decode content
        from ..utils.text_processor import TextProcessor
        return TextProcessor.validate_encoding(content_bytes)
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting to requests."""
        async with self._rate_limit_lock:
            now = datetime.now()
            
            # Remove old request times (older than 1 minute)
            cutoff_time = now - timedelta(minutes=1)
            self._request_times = [t for t in self._request_times if t > cutoff_time]
            
            # Check if we've exceeded rate limit
            if len(self._request_times) >= self.config.requests_per_minute:
                # Calculate wait time
                oldest_request = min(self._request_times)
                wait_time = 60 - (now - oldest_request).total_seconds()
                
                if wait_time > 0:
                    logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)
            
            # Add current request time
            self._request_times.append(now)
            
            # Apply minimum delay between requests
            if self.config.delay_between_requests > 0:
                await asyncio.sleep(self.config.delay_between_requests)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            async with self._session_lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.config.max_concurrent_requests,
                        verify_ssl=self.config.verify_ssl
                    )
                    
                    timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                    
                    headers = {
                        'User-Agent': self.config.user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                    }
                    
                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout,
                        headers=headers
                    )
        
        return self._session
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
