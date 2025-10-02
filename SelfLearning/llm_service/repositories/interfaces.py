"""
Repository interfaces for content management.

This module defines abstract interfaces for content repositories,
allowing for different implementations (file-based, database, API, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
from enum import Enum

from .models import ContentMetadata, ProcessingStatus


class ContentSource(Enum):
    """Sources of blog content."""
    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    API = "api"
    WEB_CRAWLER = "web_crawler"
    USER_INPUT = "user_input"


class ContentFilter:
    """Filter criteria for content queries."""
    
    def __init__(
        self,
        source: Optional[ContentSource] = None,
        status: Optional[ProcessingStatus] = None,
        content_type: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        min_word_count: Optional[int] = None,
        max_word_count: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        has_questions: Optional[bool] = None,
        tags: Optional[List[str]] = None
    ):
        self.source = source
        self.status = status
        self.content_type = content_type
        self.difficulty_level = difficulty_level
        self.min_word_count = min_word_count
        self.max_word_count = max_word_count
        self.created_after = created_after
        self.created_before = created_before
        self.has_questions = has_questions
        self.tags = tags or []


# 'IBlogContent' is now defined in models.py to avoid circular imports


class IContentRepository(ABC):
    """Abstract interface for content repositories."""
    
    @abstractmethod
    async def get_by_id(self, content_id: str) -> Optional['IBlogContent']:
        """
        Retrieve content by ID.
        
        Args:
            content_id: Unique identifier for the content
            
        Returns:
            BlogContent object or None if not found
        """
        pass
    
    @abstractmethod
    async def get_all(
        self, 
        filter_criteria: Optional[ContentFilter] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List['IBlogContent']:
        """
        Retrieve all content matching filter criteria.
        
        Args:
            filter_criteria: Optional filter to apply
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of BlogContent objects
        """
        pass
    
    @abstractmethod
    async def get_unprocessed(self, limit: Optional[int] = None) -> List['IBlogContent']:
        """
        Get content that hasn't been processed for question generation.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of unprocessed BlogContent objects
        """
        pass
    
    @abstractmethod
    async def save(self, content: 'IBlogContent') -> str:
        """
        Save content to repository.
        
        Args:
            content: BlogContent object to save
            
        Returns:
            Content ID of saved content
        """
        pass
    
    @abstractmethod
    async def update_status(self, content_id: str, status: ProcessingStatus) -> bool:
        """
        Update processing status of content.
        
        Args:
            content_id: ID of content to update
            status: New processing status
            
        Returns:
            True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def update_metadata(self, content_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update content metadata.
        
        Args:
            content_id: ID of content to update
            metadata: Metadata dictionary to merge
            
        Returns:
            True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, content_id: str) -> bool:
        """
        Delete content from repository.
        
        Args:
            content_id: ID of content to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        filter_criteria: Optional[ContentFilter] = None,
        limit: int = 10
    ) -> List['IBlogContent']:
        """
        Search content by text query.
        
        Args:
            query: Search query string
            filter_criteria: Optional additional filters
            limit: Maximum number of results
            
        Returns:
            List of matching BlogContent objects
        """
        pass
    
    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get repository statistics.
        
        Returns:
            Dictionary with statistics (total count, status breakdown, etc.)
        """
        pass
    
    @abstractmethod
    async def stream_all(
        self, 
        filter_criteria: Optional[ContentFilter] = None,
        batch_size: int = 100
    ) -> AsyncGenerator[List['IBlogContent'], None]:
        """
        Stream all content in batches for memory-efficient processing.
        
        Args:
            filter_criteria: Optional filter to apply
            batch_size: Number of items per batch
            
        Yields:
            Batches of BlogContent objects
        """
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> ContentSource:
        """Get the source type of this repository."""
        pass
