"""
Content extraction implementation for web pages.

Provides robust content extraction with proper error handling,
metadata extraction, and text processing capabilities.
"""

from typing import Dict, Optional, Any, List
from bs4 import BeautifulSoup, Tag
import logging
from ..core.interfaces import IContentExtractor
from ..utils.text_processor import TextProcessor
from ..utils.exceptions import ContentExtractionError

logger = logging.getLogger(__name__)


class ContentExtractor(IContentExtractor):
    """Extracts and processes content from web pages."""
    
    def __init__(self, parser: str = "html.parser"):
        """
        Initialize content extractor.
        
        Args:
            parser: BeautifulSoup parser to use
        """
        self.parser = parser
        self.text_processor = TextProcessor()
    
    def extract_text(self, html_content: str) -> str:
        """
        Extract clean text content from HTML.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned text content
            
        Raises:
            ContentExtractionError: If extraction fails
        """
        if not html_content:
            raise ContentExtractionError("HTML content cannot be empty")
        
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, self.parser)
            
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "aside"]):
                element.decompose()
            
            # Extract structured content with DOM information
            structured_content = self.extract_structured_content(html_content)
            
            # Also extract focused article content
            article_content = self.extract_article_content(html_content)
            
            # Format structured content into readable text
            formatted_text = self._format_structured_content(structured_content)
            
            # If we found article content, prepend it (prioritize article content)
            if article_content.get('main_text') and len(article_content['main_text']) > 100:  # Reduced threshold
                formatted_text = f"=== MAIN ARTICLE CONTENT ===\n{article_content['main_text']}\n\n{formatted_text}"
            
            # If we still don't have much content, try a more lenient extraction
            if len(formatted_text) < 200:
                soup = BeautifulSoup(html_content, self.parser)
                # Remove only the most obvious non-content elements
                for element in soup(["script", "style", "nav", "footer", "aside"]):
                    element.decompose()
                
                # Try to find any substantial text content
                fallback_text = soup.get_text(separator='\n', strip=True)
                if len(fallback_text) > len(formatted_text):
                    formatted_text = f"=== FALLBACK CONTENT ===\n{fallback_text}\n\n{formatted_text}"
            
            logger.debug(f"Extracted {len(formatted_text)} characters of structured text content")
            return formatted_text
            
        except Exception as e:
            logger.error(f"Failed to extract text content: {e}")
            raise ContentExtractionError(f"Text extraction failed: {e}")
    
    def extract_metadata(self, html_content: str) -> Dict[str, str]:
        """
        Extract metadata from HTML content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {}
        
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text(strip=True)
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                metadata['description'] = meta_desc.get('content', '').strip()
            
            # Extract meta keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords:
                metadata['keywords'] = meta_keywords.get('content', '').strip()
            
            # Extract author
            meta_author = soup.find('meta', attrs={'name': 'author'})
            if meta_author:
                metadata['author'] = meta_author.get('content', '').strip()
            
            # Extract Open Graph data
            og_title = soup.find('meta', property='og:title')
            if og_title:
                metadata['og_title'] = og_title.get('content', '').strip()
            
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                metadata['og_description'] = og_desc.get('content', '').strip()
            
            # Extract canonical URL
            canonical = soup.find('link', rel='canonical')
            if canonical:
                metadata['canonical_url'] = canonical.get('href', '').strip()
            
            # Extract language
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                metadata['language'] = html_tag.get('lang').strip()
            
            # Extract charset
            charset_meta = soup.find('meta', charset=True)
            if charset_meta:
                metadata['charset'] = charset_meta.get('charset', '').strip()
            else:
                # Try http-equiv content-type
                content_type = soup.find('meta', {'http-equiv': 'content-type'})
                if content_type:
                    content = content_type.get('content', '')
                    if 'charset=' in content:
                        metadata['charset'] = content.split('charset=')[1].strip()
            
            logger.debug(f"Extracted {len(metadata)} metadata fields")
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract some metadata: {e}")
            return metadata
    
    def _extract_main_content(self, soup: BeautifulSoup) -> Optional[Tag]:
        """
        Extract main content from HTML using semantic elements.
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            Main content element or None
        """
        # Priority order for content extraction
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.main-content',
            '.content',
            '#main',
            '#content',
            '.post-content',
            '.entry-content'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element and self._has_substantial_content(element):
                return element
        
        return None
    
    def _has_substantial_content(self, element: Tag) -> bool:
        """
        Check if an element has substantial text content.
        
        Args:
            element: HTML element to check
            
        Returns:
            True if element has substantial content
        """
        if not element:
            return False
        
        text = element.get_text(strip=True)
        return len(text) > 100  # Minimum content threshold
    
    def extract_links(self, html_content: str, base_url: str = "") -> Dict[str, str]:
        """
        Extract links from HTML content.
        
        Args:
            html_content: Raw HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            Dictionary of link text to URL mappings
        """
        links = {}
        
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').strip()
                text = link.get_text(strip=True)
                
                if href and text:
                    # Resolve relative URLs if base_url provided
                    if base_url and not href.startswith(('http://', 'https://')):
                        from urllib.parse import urljoin
                        href = urljoin(base_url, href)
                    
                    links[text] = href
            
            return links
            
        except Exception as e:
            logger.warning(f"Failed to extract links: {e}")
            return links
    
    def extract_structured_content(self, html_content: str) -> Dict[str, Any]:
        """
        Extract structured content with DOM information including headlines and paragraphs.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Dictionary containing structured content with DOM info
        """
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "aside", "header"]):
                element.decompose()
            
            structured_content = {
                'headlines': self._extract_headlines(soup),
                'paragraphs': self._extract_paragraphs(soup),
                'main_content': self._extract_main_text(soup)
            }
            
            return structured_content
            
        except Exception as e:
            logger.error(f"Failed to extract structured content: {e}")
            raise ContentExtractionError(f"Structured content extraction failed: {e}")
    
    def _extract_headlines(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract main content headlines, filtering out navigation and sidebar headlines."""
        headlines = []
        
        # Find all heading elements (h1-h6)
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = heading.get_text(strip=True)
            
            if text and self._is_main_content_headline(heading, text):
                headline_info = {
                    'tag': heading.name,
                    'level': int(heading.name[1]),  # Extract number from h1, h2, etc.
                    'text': text,
                    'classes': heading.get('class', []),
                    'id': heading.get('id', ''),
                    'xpath': self._get_xpath(heading)
                }
                headlines.append(headline_info)
        
        return headlines
    
    def _is_main_content_headline(self, heading, text: str) -> bool:
        """Determine if a headline is main content or sidebar/navigation."""
        if not text or len(text) < 3:
            return False
        
        # Get heading classes and parent classes for filtering
        heading_classes = ' '.join(heading.get('class', [])).lower()
        parent_classes = ' '.join(heading.parent.get('class', [])).lower() if heading.parent else ''
        all_classes = heading_classes + ' ' + parent_classes
        
        # Skip headlines that are clearly not main content (reduced list)
        skip_patterns = [
            'nav', 'menu', 'sidebar', 'widget', 'footer', 'header',
            'ad', 'advertisement', 'promo', 'banner',
            'social', 'share', 'follow', 'subscribe',
            'related', 'recommend', 'trending', 'popular',
            'comment', 'tag', 'breadcrumb'
        ]
        
        for pattern in skip_patterns:
            if pattern in all_classes:
                return False
        
        # Skip common navigation/UI headlines (more specific)
        ui_headlines = [
            'menu', 'navigation', 'search', 'login', 'sign up',
            'follow us', 'subscribe', 'newsletter',
            'visual stories', 'photostories', 'photo stories',
            'bigg boss', 'celebrity gossip', 'bollywood news'
        ]
        
        text_lower = text.lower()
        for ui_headline in ui_headlines:
            if ui_headline in text_lower:
                return False
        
        return True
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract main content paragraphs, filtering out sidebar and navigation content."""
        paragraphs = []
        
        # Find all paragraph elements
        for i, para in enumerate(soup.find_all('p')):
            text = para.get_text(strip=True)
            
            # Filter criteria for main content paragraphs
            if self._is_main_content_paragraph(para, text):
                para_info = {
                    'index': i,
                    'text': text,
                    'classes': para.get('class', []),
                    'id': para.get('id', ''),
                    'xpath': self._get_xpath(para),
                    'word_count': len(text.split()),
                    'parent_tag': para.parent.name if para.parent else '',
                    'has_links': bool(para.find_all('a')),
                    'has_images': bool(para.find_all('img'))
                }
                paragraphs.append(para_info)
        
        return paragraphs
    
    def _is_main_content_paragraph(self, para, text: str) -> bool:
        """Determine if a paragraph is main content or sidebar/navigation."""
        if not text or len(text) < 20:  # Reduced minimum length
            return False
        
        # Get paragraph classes and parent classes for filtering
        para_classes = ' '.join(para.get('class', [])).lower()
        parent_classes = ' '.join(para.parent.get('class', [])).lower() if para.parent else ''
        all_classes = para_classes + ' ' + parent_classes
        
        # Skip paragraphs that are clearly not main content (reduced list)
        skip_patterns = [
            'nav', 'menu', 'sidebar', 'widget', 'footer', 'header',
            'ad', 'advertisement', 'promo', 'banner',
            'social', 'share', 'follow', 'subscribe',
            'related', 'recommend', 'trending', 'popular',
            'comment', 'reply', 'feedback',
            'tag', 'category', 'breadcrumb',
            'video', 'gallery', 'slideshow'
        ]
        
        for pattern in skip_patterns:
            if pattern in all_classes:
                return False
        
        # Skip very short paragraphs that are likely navigation/UI text
        if len(text.split()) < 5:  # Reduced from 8 to 5 words
            return False
        
        # Skip paragraphs that look like navigation or UI elements (more specific)
        ui_indicators = [
            'click here', 'read more', 'view all', 'see more', 'load more',
            'sign up', 'log in', 'subscribe', 'follow us', 'share this',
            'next article', 'previous article',
            'bigg boss', 'celebrity gossip', 'bollywood news',
            'makeup ideas', 'fashion tips', 'beauty secrets'
        ]
        
        text_lower = text.lower()
        # Only filter if it's a short paragraph AND contains UI indicators
        for indicator in ui_indicators:
            if indicator in text_lower and len(text.split()) < 10:  # Reduced threshold
                return False
        
        return True
    
    def _extract_lists(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract lists (ul, ol) with their items."""
        lists = []
        
        for list_elem in soup.find_all(['ul', 'ol']):
            items = []
            for li in list_elem.find_all('li', recursive=False):  # Direct children only
                item_text = li.get_text(strip=True)
                if item_text:
                    items.append({
                        'text': item_text,
                        'classes': li.get('class', []),
                        'has_links': bool(li.find_all('a'))
                    })
            
            if items:
                list_info = {
                    'type': list_elem.name,  # 'ul' or 'ol'
                    'classes': list_elem.get('class', []),
                    'id': list_elem.get('id', ''),
                    'items': items,
                    'item_count': len(items),
                    'xpath': self._get_xpath(list_elem)
                }
                lists.append(list_info)
        
        return lists
    
    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """Extract main text content from semantic elements."""
        # Priority order for content extraction with more specific selectors
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.article-content',
            '.story-content', 
            '.post-content',
            '.entry-content',
            '.main-content',
            '.content-body',
            '.article-body',
            '.story-body',
            '.text-content',
            '.content',
            '#main-content',
            '#article-content',
            '#story-content',
            '#main',
            '#content',
            # News site specific selectors
            '.Normal',  # Times of India
            '.story_content',
            '.article_content',
            '.post_content',
            '.entry_content'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element and self._has_substantial_content(element):
                # Remove unwanted elements from the main content
                self._clean_content_element(element)
                return element.get_text(separator='\n', strip=True)
        
        # Try to find the largest text block
        main_content = self._find_largest_text_block(soup)
        if main_content:
            return main_content
        
        # Fallback to body content with cleaning
        body = soup.find('body')
        if body:
            # Remove navigation, sidebar, and footer content
            self._remove_non_content_elements(body)
            return body.get_text(separator='\n', strip=True)
        
        return soup.get_text(separator='\n', strip=True)
    
    def _get_xpath(self, element) -> str:
        """Generate a simple XPath for an element."""
        if not element or not element.parent:
            return ''
        
        path_parts = []
        current = element
        
        while current and current.name:
            siblings = current.parent.find_all(current.name, recursive=False) if current.parent else []
            if len(siblings) > 1:
                index = siblings.index(current) + 1
                path_parts.append(f"{current.name}[{index}]")
            else:
                path_parts.append(current.name)
            current = current.parent
        
        path_parts.reverse()
        return '/' + '/'.join(path_parts) if path_parts else ''
    
    def _format_structured_content(self, structured_content: Dict[str, Any]) -> str:
        """Format structured content into readable text."""
        output_lines = []
        
        # Add headlines section
        if structured_content.get('headlines'):
            output_lines.append("=== HEADLINES ===")
            for headline in structured_content['headlines']:
                level_prefix = "#" * headline['level']
                output_lines.append(f"{level_prefix} {headline['text']}")
                if headline.get('classes'):
                    output_lines.append(f"   [DOM: {headline['tag']}, classes: {', '.join(headline['classes'])}]")
                else:
                    output_lines.append(f"   [DOM: {headline['tag']}]")
            output_lines.append("")
        
        # Add paragraphs section
        if structured_content.get('paragraphs'):
            output_lines.append("=== CONTENT PARAGRAPHS ===")
            for i, para in enumerate(structured_content['paragraphs'], 1):
                output_lines.append(f"[Paragraph {i}] ({para['word_count']} words)")
                if para.get('classes'):
                    output_lines.append(f"   [DOM: p.{'.'.join(para['classes'])}, parent: {para['parent_tag']}]")
                else:
                    output_lines.append(f"   [DOM: p, parent: {para['parent_tag']}]")
                output_lines.append(f"   {para['text']}")
                output_lines.append("")
        
        # Lists removed to focus on main content only
        
        # Add main content if no structured content found
        if not any([structured_content.get('headlines'), 
                   structured_content.get('paragraphs')]):
            output_lines.append("=== MAIN CONTENT ===")
            main_text = structured_content.get('main_content', '')
            if main_text:
                # Split into paragraphs for better readability
                paragraphs = [p.strip() for p in main_text.split('\n\n') if p.strip()]
                for i, para in enumerate(paragraphs, 1):
                    if len(para) > 50:  # Only include substantial paragraphs
                        output_lines.append(f"[Content Block {i}]")
                        output_lines.append(f"   {para}")
                        output_lines.append("")
        
        return '\n'.join(output_lines)
    
    def _clean_content_element(self, element) -> None:
        """Remove unwanted elements from main content."""
        # Remove elements that are typically not main content
        unwanted_selectors = [
            'nav', 'aside', 'footer', 'header',
            '.navigation', '.nav', '.sidebar', '.menu',
            '.advertisement', '.ad', '.ads', '.advert',
            '.social', '.share', '.sharing',
            '.related', '.recommended', '.suggestions',
            '.comments', '.comment-section',
            '.breadcrumb', '.breadcrumbs',
            '.tags', '.tag-list',
            '.author-bio', '.author-info',
            '.newsletter', '.subscription',
            '.popup', '.modal', '.overlay'
        ]
        
        for selector in unwanted_selectors:
            for unwanted in element.select(selector):
                unwanted.decompose()
    
    def _remove_non_content_elements(self, soup: BeautifulSoup) -> None:
        """Remove non-content elements from the entire page."""
        # Remove common non-content elements - expanded list
        non_content_elements = [
            'nav', 'aside', 'footer', 'header', 'form',
            'script', 'style', 'noscript', 'iframe',
            # Navigation and menus
            '[class*="nav"]', '[class*="menu"]', '[class*="breadcrumb"]',
            '[class*="sidebar"]', '[class*="widget"]',
            # Advertisements and promotions
            '[class*="ad"]', '[class*="advertisement"]', '[class*="promo"]',
            '[class*="banner"]', '[class*="sponsor"]',
            # Social and sharing
            '[class*="social"]', '[class*="share"]', '[class*="follow"]',
            '[class*="subscribe"]', '[class*="newsletter"]',
            # Related content and recommendations
            '[class*="related"]', '[class*="recommend"]', '[class*="trending"]',
            '[class*="popular"]', '[class*="more-"]', '[class*="other"]',
            # Comments and user interaction
            '[class*="comment"]', '[class*="reply"]', '[class*="feedback"]',
            # Author and metadata (keep minimal)
            '[class*="author-bio"]', '[class*="author-info"]',
            # Tags and categories (excessive)
            '[class*="tag"]', '[class*="category"]', '[class*="label"]',
            # Utility elements
            '[class*="print"]', '[class*="email"]', '[class*="download"]',
            '[class*="search"]', '[class*="filter"]',
            # News site specific
            '[class*="breaking"]', '[class*="live"]', '[class*="update"]',
            '[class*="ticker"]', '[class*="alert"]',
            # Video and multimedia (keep text only)
            '[class*="video"]', '[class*="gallery"]', '[class*="slideshow"]',
            # Subscription and paywall elements
            '[class*="paywall"]', '[class*="premium"]', '[class*="subscription"]'
        ]
        
        for selector in non_content_elements:
            for element in soup.select(selector):
                element.decompose()
    
    def _find_largest_text_block(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the largest block of text content on the page."""
        # Look for divs and sections with substantial text content
        candidates = []
        
        # Check all div and section elements
        for element in soup.find_all(['div', 'section', 'article']):
            if element.name in ['script', 'style', 'nav', 'aside', 'footer', 'header']:
                continue
                
            text = element.get_text(strip=True)
            if len(text) > 200:  # Minimum text length
                # Calculate text density (text vs HTML)
                html_length = len(str(element))
                text_density = len(text) / html_length if html_length > 0 else 0
                
                # Prefer elements with higher text density
                if text_density > 0.05:  # At least 5% text content (lowered threshold)
                    # Boost score for elements with very high text density
                    density_boost = 1.0
                    if text_density > 0.3:  # Very high text density
                        density_boost = 2.0
                    elif text_density > 0.2:  # High text density
                        density_boost = 1.5
                    
                    candidates.append({
                        'element': element,
                        'text': text,
                        'length': len(text),
                        'density': text_density,
                        'score': len(text) * text_density * density_boost  # Enhanced scoring
                    })
        
        if candidates:
            # Sort by score (length * density) and return the best
            best_candidate = max(candidates, key=lambda x: x['score'])
            
            # Clean the element before extracting text
            self._clean_content_element(best_candidate['element'])
            return best_candidate['element'].get_text(separator='\n', strip=True)
        
        return None
    
    def extract_article_content(self, html_content: str) -> Dict[str, Any]:
        """
        Extract main article content with better focus on actual content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Dictionary with focused article content
        """
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            # Remove unwanted elements first
            self._remove_non_content_elements(soup)
            
            # Try to find article-specific content
            article_selectors = [
                'article',
                '.article',
                '.story',
                '.post',
                '.content',
                '.main-content',
                '[role="main"]',
                'main',
                # Times of India specific selectors
                '._s30J',
                '.fewcent-124175606',
                '.js_tbl_article',
                # Other news site patterns
                '.article-body',
                '.story-body',
                '.post-body',
                '.entry-content',
                '.content-body'
            ]
            
            article_content = None
            for selector in article_selectors:
                element = soup.select_one(selector)
                if element and self._has_substantial_content(element):
                    self._clean_content_element(element)
                    article_content = element
                    break
            
            if not article_content:
                # Fallback to largest text block
                largest_text = self._find_largest_text_block(soup)
                if largest_text:
                    return {
                        'main_text': largest_text,
                        'word_count': len(largest_text.split()),
                        'extraction_method': 'largest_text_block'
                    }
            else:
                main_text = article_content.get_text(separator='\n', strip=True)
                return {
                    'main_text': main_text,
                    'word_count': len(main_text.split()),
                    'extraction_method': 'article_selector'
                }
            
            # Final fallback
            body = soup.find('body')
            if body:
                text = body.get_text(separator='\n', strip=True)
                return {
                    'main_text': text,
                    'word_count': len(text.split()),
                    'extraction_method': 'body_fallback'
                }
            
            return {
                'main_text': '',
                'word_count': 0,
                'extraction_method': 'failed'
            }
            
        except Exception as e:
            logger.error(f"Failed to extract article content: {e}")
            return {
                'main_text': '',
                'word_count': 0,
                'extraction_method': 'error',
                'error': str(e)
            }
