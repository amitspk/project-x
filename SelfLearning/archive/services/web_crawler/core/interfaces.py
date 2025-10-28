"""
Abstract interfaces for the web crawler system.

Defines contracts for crawler components to ensure proper separation of concerns
and testability through dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class ICrawler(ABC):
    """Interface for web crawling functionality."""
    
    @abstractmethod
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
        pass


class IContentExtractor(ABC):
    """Interface for content extraction from web pages."""
    
    @abstractmethod
    def extract_text(self, html_content: str) -> str:
        """
        Extract clean text content from HTML.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned text content
            
        Raises:
            ValidationError: If content is invalid
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, html_content: str) -> Dict[str, str]:
        """
        Extract metadata from HTML content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Dictionary containing metadata (title, description, etc.)
        """
        pass


class IStorage(ABC):
    """Interface for content storage operations."""
    
    @abstractmethod
    async def save_content(self, content: str, filename: str, metadata: Optional[Dict[str, Any]] = None) -> Path:
        """
        Save content to storage.
        
        Args:
            content: Content to save
            filename: Name of the file
            metadata: Optional metadata to include
            
        Returns:
            Path to the saved file
            
        Raises:
            StorageError: If saving fails
        """
        pass
    
    @abstractmethod
    def get_storage_path(self, filename: str) -> Path:
        """
        Get the full storage path for a filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            Full path to the file
        """
        pass
