"""
Text processing utilities for content extraction and cleaning.

Provides robust text processing capabilities with proper encoding handling
and content sanitization for production use.
"""

import re
from typing import Dict, List, Optional
from html import unescape
from .exceptions import ContentExtractionError


class TextProcessor:
    """Handles text processing and cleaning operations."""
    
    # Regex patterns for cleaning
    WHITESPACE_PATTERN = re.compile(r'\s+')
    SCRIPT_STYLE_PATTERN = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE)
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    MULTIPLE_NEWLINES = re.compile(r'\n\s*\n\s*\n+')
    
    @classmethod
    def clean_html_content(cls, html_content: str) -> str:
        """
        Clean HTML content and extract readable text.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned text content
            
        Raises:
            ContentExtractionError: If processing fails
        """
        if not html_content or not isinstance(html_content, str):
            raise ContentExtractionError("HTML content must be a non-empty string")
        
        try:
            # Remove script and style elements
            content = cls.SCRIPT_STYLE_PATTERN.sub('', html_content)
            
            # Remove HTML tags
            content = cls.HTML_TAG_PATTERN.sub(' ', content)
            
            # Decode HTML entities
            content = unescape(content)
            
            # Normalize whitespace
            content = cls.WHITESPACE_PATTERN.sub(' ', content)
            
            # Clean up multiple newlines
            content = cls.MULTIPLE_NEWLINES.sub('\n\n', content)
            
            # Strip and return
            return content.strip()
            
        except Exception as e:
            raise ContentExtractionError(f"Failed to clean HTML content: {e}")
    
    @classmethod
    def extract_sentences(cls, text: str, min_length: int = 10) -> List[str]:
        """
        Extract sentences from text with minimum length filtering.
        
        Args:
            text: Input text
            min_length: Minimum sentence length
            
        Returns:
            List of sentences
        """
        if not text:
            return []
        
        # Simple sentence splitting (can be enhanced with NLP libraries)
        sentences = re.split(r'[.!?]+', text)
        
        # Filter and clean sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) >= min_length:
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    @classmethod
    def extract_keywords(cls, text: str, max_keywords: int = 20) -> List[str]:
        """
        Extract potential keywords from text (basic implementation).
        
        Args:
            text: Input text
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Simple frequency counting (can be enhanced with TF-IDF)
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]
    
    @classmethod
    def truncate_text(cls, text: str, max_length: int = 1000, suffix: str = "...") -> str:
        """
        Truncate text to specified length with proper word boundaries.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add when truncated
            
        Returns:
            Truncated text
        """
        if not text or len(text) <= max_length:
            return text
        
        # Find last space before max_length
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If space is reasonably close
            truncated = truncated[:last_space]
        
        return truncated + suffix
    
    @classmethod
    def validate_encoding(cls, content: bytes) -> str:
        """
        Validate and decode content with proper encoding detection.
        
        Args:
            content: Raw bytes content
            
        Returns:
            Decoded string content
            
        Raises:
            ContentExtractionError: If encoding detection fails
        """
        if not content:
            return ""
        
        # Try common encodings
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # Fallback with error handling
        try:
            return content.decode('utf-8', errors='replace')
        except Exception as e:
            raise ContentExtractionError(f"Failed to decode content: {e}")
    
    @classmethod
    def format_metadata(cls, metadata: Dict[str, str]) -> str:
        """
        Format metadata dictionary into readable text.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Formatted metadata string
        """
        if not metadata:
            return ""
        
        lines = ["=== METADATA ==="]
        for key, value in metadata.items():
            if value:
                lines.append(f"{key.title()}: {value}")
        lines.append("=" * 20)
        
        return "\n".join(lines)
