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
            'Accept-Encoding': 'gzip, deflate, br',  # Allow compression
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
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('text/html'):
                logger.warning(f"⚠️  Unexpected content type: {content_type} for {url}")
            
            # Get text with proper encoding handling
            try:
                # httpx automatically handles gzip/deflate decompression
                # But let's verify the response was properly decompressed
                content_encoding = response.headers.get('content-encoding', '').lower()
                
                # If content is still compressed, httpx should have handled it, but let's check
                if content_encoding in ['gzip', 'deflate', 'br']:
                    # httpx should have automatically decompressed, but verify it's text
                    if not isinstance(response.content, bytes) or len(response.content) == 0:
                        raise ValueError("Response content is empty")
                
                # Get text - httpx handles encoding automatically
                text = response.text
                
                # Validate that we got actual text (not binary)
                if self._is_invalid_content(text):
                    logger.warning(f"⚠️  Detected invalid/binary content for {url}")
                    logger.warning(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
                    logger.warning(f"   Content-Length: {len(response.content)} bytes")
                    logger.warning(f"   Text length: {len(text)} chars")
                    logger.warning(f"   First 200 chars: {repr(text[:200])}")
                    raise ValueError("Content appears to be binary or corrupted - cannot extract valid HTML")
                
                # Additional check: verify it looks like HTML
                if not any(tag in text.lower() for tag in ['<html', '<body', '<div', '<article', '<main', '<p']):
                    # Might be valid plain text, but for a web page it's suspicious
                    logger.warning(f"⚠️  Content doesn't appear to contain HTML tags")
                    # But don't fail if it's valid text with enough words
                    words = text.split()
                    if len(words) < 50:
                        raise ValueError("Content doesn't appear to be valid HTML or text")
                
                return text
            except ValueError:
                # Re-raise validation errors
                raise
            except Exception as e:
                logger.error(f"❌ Failed to decode HTML content: {e}")
                raise ValueError(f"Failed to extract valid HTML content: {e}")
    
    def _is_invalid_content(self, text: str) -> bool:
        """
        Check if content appears to be invalid (binary/junk data).
        
        Returns True if content is likely invalid.
        """
        if not text or len(text) < 100:
            return True
        
        # Count printable vs non-printable characters
        printable_chars = sum(1 for c in text if c.isprintable() or c.isspace())
        total_chars = len(text)
        
        # If less than 70% of characters are printable, likely binary/junk
        if total_chars > 0 and (printable_chars / total_chars) < 0.7:
            logger.warning(f"⚠️  Low printable character ratio: {printable_chars/total_chars:.2%}")
            return True
        
        # Check for high ratio of Unicode replacement characters ()
        replacement_chars = text.count('\ufffd')
        if replacement_chars > len(text) * 0.1:  # More than 10% replacement chars
            logger.warning(f"⚠️  High ratio of replacement characters: {replacement_chars}/{len(text)}")
            return True
        
        # Check if content looks like HTML (should have HTML tags)
        if '<html' not in text.lower() and '<body' not in text.lower() and '<div' not in text.lower():
            # Might be plain text, which is okay, but if it's all non-ASCII weirdness, it's suspicious
            if len(text) > 500 and replacement_chars > len(text) * 0.05:
                return True
        
        return False
    
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
        
        # Validate extracted content
        if not content or len(content.strip()) < 50:
            raise ValueError("Extracted content is too short or empty")
        
        # Additional validation: check if content looks valid
        if self._is_invalid_content(content):
            raise ValueError("Extracted content appears to be invalid/binary data")
        
        # Detect language
        language = self._detect_language(soup)
        
        # Calculate word count
        word_count = len(content.split())
        
        # Validate minimum word count
        if word_count < 10:
            raise ValueError(f"Extracted content has too few words: {word_count} (minimum: 10)")
        
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

