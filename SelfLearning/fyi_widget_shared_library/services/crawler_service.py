"""
Internal crawler service - adapted from web_crawler module.

Extracts content from web pages.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Configuration handled by service-specific configs
from fyi_widget_shared_library.models.schemas import CrawledContent

logger = logging.getLogger(__name__)


class CrawlerService:
    """Internal web crawler service."""
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: str = "BlogQA-Crawler/1.0",
        max_content_size: int = 10 * 1024 * 1024
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.max_content_size = max_content_size
    
    async def crawl_url(self, url: str) -> CrawledContent:
        """
        Crawl a URL and extract content.
        
        Args:
            url: URL to crawl
            
        Returns:
            CrawledContent with extracted data
            
        Raises:
            Exception: If crawling fails
        """
        logger.info(f"🕷️  Crawling URL: {url}")
        
        for attempt in range(self.max_retries):
            try:
                html_content = await self._fetch_html(url)
                extracted = await self._extract_content(html_content, url)
                
                logger.info(f"✅ Crawled successfully: {url} ({extracted.word_count} words)")
                return extracted
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"⚠️  Retry {attempt + 1}/{self.max_retries} for {url}: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed to crawl {url}: {e}")
                    raise
    
    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from URL."""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10)
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            # Check content size
            if len(response.content) > self.max_content_size:
                raise ValueError(f"Content too large: {len(response.content)} bytes")
            
            return response.text
    
    async def _extract_content(self, html: str, url: str) -> CrawledContent:
        """Extract meaningful content from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
            tag.decompose()
        
        # Extract title
        title = self._extract_title(soup)
        
        # Extract main content
        content = self._extract_main_content(soup)
        
        # Detect language
        language = self._detect_language(soup)
        
        # Calculate word count
        word_count = len(content.split())
        
        # Parse domain for metadata
        parsed_url = urlparse(url)
        metadata = {
            'domain': parsed_url.netloc,
            'path': parsed_url.path,
            'extracted_at': None  # Will be set by storage service
        }
        
        return CrawledContent(
            url=url,
            title=title,
            content=content,
            language=language,
            word_count=word_count,
            metadata=metadata
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try og:title first
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']
        
        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        return "Untitled"
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content."""
        # Try to find main article container
        article = soup.find('article')
        if article:
            return self._clean_text(article.get_text())
        
        # Try main tag
        main = soup.find('main')
        if main:
            return self._clean_text(main.get_text())
        
        # Try common blog content classes
        content_classes = [
            'post-content', 'article-content', 'entry-content',
            'blog-post', 'post-body', 'content', 'main-content'
        ]
        
        for cls in content_classes:
            content_div = soup.find('div', class_=cls)
            if content_div:
                return self._clean_text(content_div.get_text())
        
        # Fallback: get all paragraphs
        paragraphs = soup.find_all('p')
        if paragraphs:
            text = ' '.join(p.get_text() for p in paragraphs)
            return self._clean_text(text)
        
        # Last resort: body text
        return self._clean_text(soup.get_text())
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        return ' '.join(lines)
    
    def _detect_language(self, soup: BeautifulSoup) -> str:
        """Detect page language."""
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            lang = html_tag['lang']
            # Normalize language code (e.g., "en-US" -> "en")
            return lang.split('-')[0].lower()
        
        # Check meta content-language
        lang_meta = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if lang_meta and lang_meta.get('content'):
            lang = lang_meta['content']
            return lang.split('-')[0].lower()
        
        # Default to English
        return 'en'

