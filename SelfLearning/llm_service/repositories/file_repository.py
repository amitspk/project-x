"""
File-based content repository implementation.

This module provides a repository implementation that reads blog content
from the crawled_content folder structure and manages it in memory with
optional persistence to JSON files.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import asyncio
import re

from .interfaces import IContentRepository, ContentSource, ContentFilter
from .models import BlogContent, ContentMetadata, ProcessingStatus, IBlogContent
from ..utils.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


class FileContentRepository(IContentRepository):
    """File-based implementation of content repository."""
    
    def __init__(
        self,
        crawled_content_path: str = "crawled_content",
        index_file_path: Optional[str] = None,
        auto_scan: bool = True
    ):
        """
        Initialize file repository.
        
        Args:
            crawled_content_path: Path to crawled content directory
            index_file_path: Optional path to index file for persistence
            auto_scan: Whether to automatically scan for new files
        """
        self.crawled_content_path = Path(crawled_content_path)
        self.index_file_path = Path(index_file_path) if index_file_path else None
        self.auto_scan = auto_scan
        
        # In-memory content store
        self._content_store: Dict[str, BlogContent] = {}
        self._initialized = False
        
        logger.info(f"Initialized FileContentRepository with path: {self.crawled_content_path}")
    
    async def initialize(self):
        """Initialize the repository by scanning for content."""
        if self._initialized:
            return
        
        logger.info("Initializing file content repository...")
        
        # Load existing index if available
        if self.index_file_path and self.index_file_path.exists():
            await self._load_index()
        
        # Scan for content files
        if self.auto_scan:
            await self._scan_content_directory()
        
        self._initialized = True
        logger.info(f"Repository initialized with {len(self._content_store)} content items")
    
    @property
    def source_type(self) -> ContentSource:
        return ContentSource.FILE_SYSTEM
    
    async def get_by_id(self, content_id: str) -> Optional[IBlogContent]:
        """Retrieve content by ID."""
        await self._ensure_initialized()
        return self._content_store.get(content_id)
    
    async def get_all(
        self,
        filter_criteria: Optional[ContentFilter] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[IBlogContent]:
        """Retrieve all content matching filter criteria."""
        await self._ensure_initialized()
        
        # Get all content
        all_content = list(self._content_store.values())
        
        # Apply filters
        if filter_criteria:
            all_content = self._apply_filter(all_content, filter_criteria)
        
        # Sort by creation date (newest first)
        all_content.sort(key=lambda x: x.metadata.created_date, reverse=True)
        
        # Apply pagination
        end_index = offset + limit if limit else len(all_content)
        return all_content[offset:end_index]
    
    async def get_unprocessed(self, limit: Optional[int] = None) -> List[IBlogContent]:
        """Get content that hasn't been processed for question generation."""
        filter_criteria = ContentFilter(status=ProcessingStatus.PENDING)
        return await self.get_all(filter_criteria, limit=limit)
    
    async def save(self, content: IBlogContent) -> str:
        """Save content to repository."""
        await self._ensure_initialized()
        
        self._content_store[content.content_id] = content
        
        # Persist index if configured
        if self.index_file_path:
            await self._save_index()
        
        logger.info(f"Saved content: {content.content_id}")
        return content.content_id
    
    async def update_status(self, content_id: str, status: ProcessingStatus) -> bool:
        """Update processing status of content."""
        await self._ensure_initialized()
        
        content = self._content_store.get(content_id)
        if not content:
            return False
        
        content.set_status(status)
        
        # Persist index if configured
        if self.index_file_path:
            await self._save_index()
        
        logger.info(f"Updated status for {content_id}: {status.value}")
        return True
    
    async def update_metadata(self, content_id: str, metadata: Dict[str, Any]) -> bool:
        """Update content metadata."""
        await self._ensure_initialized()
        
        content = self._content_store.get(content_id)
        if not content:
            return False
        
        content.update_metadata(metadata)
        
        # Persist index if configured
        if self.index_file_path:
            await self._save_index()
        
        logger.info(f"Updated metadata for {content_id}")
        return True
    
    async def delete(self, content_id: str) -> bool:
        """Delete content from repository."""
        await self._ensure_initialized()
        
        if content_id in self._content_store:
            del self._content_store[content_id]
            
            # Persist index if configured
            if self.index_file_path:
                await self._save_index()
            
            logger.info(f"Deleted content: {content_id}")
            return True
        
        return False
    
    async def search(
        self,
        query: str,
        filter_criteria: Optional[ContentFilter] = None,
        limit: int = 10
    ) -> List[IBlogContent]:
        """Search content by text query."""
        await self._ensure_initialized()
        
        query_lower = query.lower()
        matching_content = []
        
        for content in self._content_store.values():
            # Search in title and content
            if (query_lower in content.title.lower() or 
                query_lower in content.content.lower() or
                any(query_lower in tag.lower() for tag in content.metadata.tags)):
                
                matching_content.append(content)
        
        # Apply additional filters
        if filter_criteria:
            matching_content = self._apply_filter(matching_content, filter_criteria)
        
        # Sort by relevance (simple scoring based on title matches)
        def relevance_score(content):
            score = 0
            if query_lower in content.title.lower():
                score += 10
            score += content.content.lower().count(query_lower)
            return score
        
        matching_content.sort(key=relevance_score, reverse=True)
        
        return matching_content[:limit]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        await self._ensure_initialized()
        
        total_count = len(self._content_store)
        status_counts = {}
        content_type_counts = {}
        total_word_count = 0
        
        for content in self._content_store.values():
            # Status breakdown
            status = content.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Content type breakdown
            content_type = content.metadata.content_type
            content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
            
            # Total word count
            total_word_count += content.get_word_count()
        
        return {
            'total_content': total_count,
            'status_breakdown': status_counts,
            'content_type_breakdown': content_type_counts,
            'total_word_count': total_word_count,
            'average_word_count': total_word_count // total_count if total_count > 0 else 0,
            'source_type': self.source_type.value,
            'last_updated': datetime.now().isoformat()
        }
    
    async def stream_all(
        self,
        filter_criteria: Optional[ContentFilter] = None,
        batch_size: int = 100
    ) -> AsyncGenerator[List[IBlogContent], None]:
        """Stream all content in batches."""
        await self._ensure_initialized()
        
        all_content = list(self._content_store.values())
        
        # Apply filters
        if filter_criteria:
            all_content = self._apply_filter(all_content, filter_criteria)
        
        # Yield in batches
        for i in range(0, len(all_content), batch_size):
            batch = all_content[i:i + batch_size]
            yield batch
            # Small delay to prevent blocking
            await asyncio.sleep(0.01)
    
    async def scan_for_new_content(self) -> int:
        """Manually scan for new content files."""
        initial_count = len(self._content_store)
        await self._scan_content_directory()
        new_count = len(self._content_store) - initial_count
        
        if new_count > 0:
            logger.info(f"Found {new_count} new content files")
            if self.index_file_path:
                await self._save_index()
        
        return new_count
    
    async def _ensure_initialized(self):
        """Ensure repository is initialized."""
        if not self._initialized:
            await self.initialize()
    
    async def _scan_content_directory(self):
        """Scan the crawled content directory for files."""
        if not self.crawled_content_path.exists():
            logger.warning(f"Crawled content directory does not exist: {self.crawled_content_path}")
            return
        
        logger.info(f"Scanning content directory: {self.crawled_content_path}")
        
        # Find all .txt files (excluding .meta.json files)
        content_files = list(self.crawled_content_path.rglob("*.txt"))
        
        new_files_count = 0
        for file_path in content_files:
            try:
                # Generate content ID from path
                content_id = self._generate_content_id_from_path(file_path)
                
                # Skip if already loaded and file hasn't changed
                if content_id in self._content_store:
                    existing_content = self._content_store[content_id]
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if existing_content.metadata.updated_date >= file_mtime:
                        continue  # File hasn't changed
                
                # Load content from file
                blog_content = BlogContent.from_crawled_file(file_path, content_id)
                self._content_store[content_id] = blog_content
                new_files_count += 1
                
                logger.debug(f"Loaded content: {content_id}")
                
            except Exception as e:
                logger.error(f"Failed to load content from {file_path}: {e}")
                continue
        
        logger.info(f"Loaded {new_files_count} new content files")
    
    def _generate_content_id_from_path(self, file_path: Path) -> str:
        """Generate content ID from file path."""
        # Remove the base crawled_content_path to get relative path
        try:
            relative_path = file_path.relative_to(self.crawled_content_path)
            # Use directory and filename to create ID
            parts = list(relative_path.parts[:-1]) + [relative_path.stem]
            content_id = "_".join(parts).replace(" ", "_").replace("-", "_")
            # Clean up the ID
            content_id = re.sub(r'[^\w_]', '_', content_id)
            return content_id
        except ValueError:
            # Fallback if path is not relative to crawled_content_path
            return file_path.stem
    
    def _apply_filter(self, content_list: List[IBlogContent], filter_criteria: ContentFilter) -> List[IBlogContent]:
        """Apply filter criteria to content list."""
        filtered_content = []
        
        for content in content_list:
            # Check status filter
            if filter_criteria.status and content.status != filter_criteria.status:
                continue
            
            # Check content type filter
            if filter_criteria.content_type and content.metadata.content_type != filter_criteria.content_type:
                continue
            
            # Check difficulty level filter
            if filter_criteria.difficulty_level and content.metadata.difficulty_level != filter_criteria.difficulty_level:
                continue
            
            # Check word count filters
            word_count = content.get_word_count()
            if filter_criteria.min_word_count and word_count < filter_criteria.min_word_count:
                continue
            if filter_criteria.max_word_count and word_count > filter_criteria.max_word_count:
                continue
            
            # Check date filters
            created_date = content.metadata.created_date
            if filter_criteria.created_after and created_date < filter_criteria.created_after:
                continue
            if filter_criteria.created_before and created_date > filter_criteria.created_before:
                continue
            
            # Check questions filter
            if filter_criteria.has_questions is not None:
                if filter_criteria.has_questions != content.metadata.questions_generated:
                    continue
            
            # Check tags filter
            if filter_criteria.tags:
                content_tags = set(tag.lower() for tag in content.metadata.tags)
                filter_tags = set(tag.lower() for tag in filter_criteria.tags)
                if not filter_tags.intersection(content_tags):
                    continue
            
            filtered_content.append(content)
        
        return filtered_content
    
    async def _load_index(self):
        """Load content index from file."""
        try:
            with open(self.index_file_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            for content_data in index_data.get('content', []):
                content = BlogContent.from_dict(content_data)
                self._content_store[content.content_id] = content
            
            logger.info(f"Loaded {len(self._content_store)} items from index file")
            
        except Exception as e:
            logger.error(f"Failed to load index file: {e}")
    
    async def _save_index(self):
        """Save content index to file."""
        try:
            # Ensure directory exists
            if self.index_file_path.parent:
                self.index_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            index_data = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'source_type': self.source_type.value,
                'content': [content.to_dict() for content in self._content_store.values()]
            }
            
            with open(self.index_file_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved index with {len(self._content_store)} items")
            
        except Exception as e:
            logger.error(f"Failed to save index file: {e}")
    
    def __str__(self) -> str:
        return f"FileContentRepository(path='{self.crawled_content_path}', items={len(self._content_store)})"
