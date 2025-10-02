"""
Data models for the repository layer.

This module defines the data structures used by content repositories
for managing blog content and metadata.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pathlib import Path

# Avoid circular import - define interface locally
from abc import ABC, abstractmethod


class ProcessingStatus(Enum):
    """Processing status of blog content."""
    PENDING = "pending"           # Not yet processed
    PROCESSING = "processing"     # Currently being processed
    COMPLETED = "completed"       # Successfully processed
    FAILED = "failed"            # Processing failed
    SKIPPED = "skipped"          # Skipped due to filters/rules


@dataclass
class ContentMetadata:
    """Metadata associated with blog content."""
    
    # Basic metadata
    url: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    created_date: datetime = field(default_factory=datetime.now)
    updated_date: datetime = field(default_factory=datetime.now)
    
    # Content classification
    content_type: str = "article"           # article, tutorial, news, review, etc.
    difficulty_level: str = "intermediate"  # beginner, intermediate, advanced
    language: str = "en"
    tags: List[str] = field(default_factory=list)
    
    # Content metrics
    word_count: int = 0
    estimated_reading_time: int = 0  # minutes
    
    # Processing metadata
    source: str = "unknown"          # file_system, database, api, etc.
    source_path: Optional[str] = None
    content_hash: Optional[str] = None
    
    # Question generation metadata
    questions_generated: bool = False
    questions_file_path: Optional[str] = None
    question_count: int = 0
    average_confidence: float = 0.0
    
    # Custom metadata
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.published_date:
            data['published_date'] = self.published_date.isoformat()
        data['created_date'] = self.created_date.isoformat()
        data['updated_date'] = self.updated_date.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentMetadata':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        if data.get('published_date'):
            data['published_date'] = datetime.fromisoformat(data['published_date'])
        if data.get('created_date'):
            data['created_date'] = datetime.fromisoformat(data['created_date'])
        if data.get('updated_date'):
            data['updated_date'] = datetime.fromisoformat(data['updated_date'])
        
        return cls(**data)


class IBlogContent(ABC):
    """Interface for blog content objects."""
    
    @property
    @abstractmethod
    def content_id(self) -> str:
        """Get unique content identifier."""
        pass
    
    @property
    @abstractmethod
    def title(self) -> str:
        """Get content title."""
        pass
    
    @property
    @abstractmethod
    def content(self) -> str:
        """Get raw content text."""
        pass
    
    @property
    @abstractmethod
    def metadata(self) -> 'ContentMetadata':
        """Get content metadata."""
        pass
    
    @property
    @abstractmethod
    def status(self) -> ProcessingStatus:
        """Get processing status."""
        pass
    
    @abstractmethod
    def get_word_count(self) -> int:
        """Get word count of content."""
        pass
    
    @abstractmethod
    def get_estimated_reading_time(self) -> int:
        """Get estimated reading time in minutes."""
        pass


class BlogContent(IBlogContent):
    """Concrete implementation of blog content."""
    
    def __init__(
        self,
        content_id: str,
        title: str,
        content: str,
        metadata: Optional[ContentMetadata] = None,
        status: ProcessingStatus = ProcessingStatus.PENDING
    ):
        self._content_id = content_id
        self._title = title
        self._content = content
        self._metadata = metadata or ContentMetadata()
        self._status = status
        
        # Update metadata with content metrics
        self._update_content_metrics()
    
    @property
    def content_id(self) -> str:
        return self._content_id
    
    @property
    def title(self) -> str:
        return self._title
    
    @property
    def content(self) -> str:
        return self._content
    
    @property
    def metadata(self) -> ContentMetadata:
        return self._metadata
    
    @property
    def status(self) -> ProcessingStatus:
        return self._status
    
    def set_status(self, status: ProcessingStatus):
        """Update processing status."""
        self._status = status
        self._metadata.updated_date = datetime.now()
    
    def get_word_count(self) -> int:
        """Get word count of content."""
        return len(self._content.split())
    
    def get_estimated_reading_time(self) -> int:
        """Get estimated reading time in minutes (200 words per minute)."""
        return max(1, self.get_word_count() // 200)
    
    def update_title(self, title: str):
        """Update content title."""
        self._title = title
        self._metadata.updated_date = datetime.now()
    
    def update_content(self, content: str):
        """Update content text."""
        self._content = content
        self._update_content_metrics()
        self._metadata.updated_date = datetime.now()
    
    def update_metadata(self, metadata_updates: Dict[str, Any]):
        """Update metadata fields."""
        for key, value in metadata_updates.items():
            if hasattr(self._metadata, key):
                setattr(self._metadata, key, value)
            else:
                self._metadata.custom_fields[key] = value
        
        self._metadata.updated_date = datetime.now()
    
    def add_tags(self, tags: List[str]):
        """Add tags to content."""
        existing_tags = set(self._metadata.tags)
        new_tags = set(tags)
        self._metadata.tags = list(existing_tags.union(new_tags))
        self._metadata.updated_date = datetime.now()
    
    def remove_tags(self, tags: List[str]):
        """Remove tags from content."""
        existing_tags = set(self._metadata.tags)
        tags_to_remove = set(tags)
        self._metadata.tags = list(existing_tags - tags_to_remove)
        self._metadata.updated_date = datetime.now()
    
    def mark_questions_generated(self, questions_file_path: str, question_count: int, average_confidence: float):
        """Mark that questions have been generated for this content."""
        self._metadata.questions_generated = True
        self._metadata.questions_file_path = questions_file_path
        self._metadata.question_count = question_count
        self._metadata.average_confidence = average_confidence
        self._metadata.updated_date = datetime.now()
        self.set_status(ProcessingStatus.COMPLETED)
    
    def _update_content_metrics(self):
        """Update content metrics in metadata."""
        self._metadata.word_count = self.get_word_count()
        self._metadata.estimated_reading_time = self.get_estimated_reading_time()
        self._metadata.content_hash = self._generate_content_hash()
    
    def _generate_content_hash(self) -> str:
        """Generate hash of content for change detection."""
        content_bytes = (self._title + self._content).encode('utf-8')
        return hashlib.sha256(content_bytes).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'content_id': self._content_id,
            'title': self._title,
            'content': self._content,
            'metadata': self._metadata.to_dict(),
            'status': self._status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlogContent':
        """Create BlogContent from dictionary."""
        metadata = ContentMetadata.from_dict(data.get('metadata', {}))
        status = ProcessingStatus(data.get('status', ProcessingStatus.PENDING.value))
        
        return cls(
            content_id=data['content_id'],
            title=data['title'],
            content=data['content'],
            metadata=metadata,
            status=status
        )
    
    @classmethod
    def from_crawled_file(cls, file_path: Path, content_id: Optional[str] = None) -> 'BlogContent':
        """
        Create BlogContent from a crawled content file.
        
        Args:
            file_path: Path to the content file
            content_id: Optional custom content ID
            
        Returns:
            BlogContent object
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Content file not found: {file_path}")
        
        # Read content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title from content or filename
        title = cls._extract_title_from_content(content) or file_path.stem
        
        # Generate content ID if not provided
        if not content_id:
            content_id = cls._generate_content_id_from_path(file_path)
        
        # Create metadata
        metadata = ContentMetadata(
            source="file_system",
            source_path=str(file_path),
            created_date=datetime.fromtimestamp(file_path.stat().st_ctime),
            updated_date=datetime.fromtimestamp(file_path.stat().st_mtime)
        )
        
        # Check for associated metadata file
        metadata_file = file_path.with_suffix('.meta.json')
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    crawled_metadata = json.load(f)
                
                # Update metadata with crawled information
                metadata.url = crawled_metadata.get('final_url')
                metadata.content_type = cls._classify_content_type(content, title)
                metadata.custom_fields.update(crawled_metadata)
                
            except Exception as e:
                # If metadata file is corrupted, continue without it
                pass
        
        return cls(
            content_id=content_id,
            title=title,
            content=content,
            metadata=metadata
        )
    
    @staticmethod
    def _extract_title_from_content(content: str) -> Optional[str]:
        """Extract title from content text."""
        lines = content.split('\n')
        
        # Look for title in metadata section
        for line in lines:
            if line.startswith('Title:'):
                return line.replace('Title:', '').strip()
        
        # Look for first heading
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line.startswith('=== ') and line.endswith(' ==='):
                continue  # Skip metadata sections
            elif line and len(line) < 100 and not line.startswith('http'):
                # First non-metadata line might be title
                return line
        
        return None
    
    @staticmethod
    def _generate_content_id_from_path(file_path: Path) -> str:
        """Generate content ID from file path."""
        # Use the directory structure to create a meaningful ID
        parts = file_path.parts
        if len(parts) >= 2:
            # Use domain and filename
            domain = parts[-2]  # Parent directory (usually domain)
            filename = file_path.stem
            return f"{domain}_{filename}"
        else:
            return file_path.stem
    
    @staticmethod
    def _classify_content_type(content: str, title: str) -> str:
        """Classify content type based on content and title."""
        content_lower = (content + " " + title).lower()
        
        type_indicators = {
            'tutorial': ['tutorial', 'guide', 'how to', 'step by step', 'walkthrough'],
            'news': ['announced', 'released', 'breaking', 'update', 'latest'],
            'review': ['review', 'comparison', 'vs', 'pros and cons'],
            'explanation': ['what is', 'understanding', 'concept', 'theory'],
            'opinion': ['opinion', 'thoughts', 'perspective', 'believe']
        }
        
        for content_type, indicators in type_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                return content_type
        
        return "article"  # Default
    
    def __str__(self) -> str:
        return f"BlogContent(id='{self.content_id}', title='{self.title[:50]}...', status={self.status.value})"
    
    def __repr__(self) -> str:
        return self.__str__()
