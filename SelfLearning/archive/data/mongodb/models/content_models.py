"""
MongoDB data models for content and analytics.

This module defines the data models used for storing content metadata,
user interactions, search analytics, and processing job information in MongoDB.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import uuid


class InteractionType(Enum):
    """Types of user interactions with content."""
    VIEW = "view"
    QUESTION_GENERATED = "question_generated"
    QUESTION_ANSWERED = "question_answered"
    SUMMARY_VIEWED = "summary_viewed"
    CONTENT_SHARED = "content_shared"
    BOOKMARK_ADDED = "bookmark_added"
    BOOKMARK_REMOVED = "bookmark_removed"
    SEARCH_PERFORMED = "search_performed"


class ProcessingStatus(Enum):
    """Status of content processing jobs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ContentMetadata:
    """
    Metadata for processed content stored in MongoDB.
    
    This model stores comprehensive information about crawled and processed
    content including summaries, questions, and processing metadata.
    """
    
    # Core identifiers
    content_id: str
    url: str
    title: str
    
    # Content data
    summary: str
    key_points: List[str] = field(default_factory=list)
    questions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    word_count: Optional[int] = None
    reading_time_minutes: Optional[int] = None
    language: str = "en"
    content_type: str = "article"
    
    # Processing information
    processed_at: datetime = field(default_factory=datetime.utcnow)
    processing_version: str = "1.0"
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    
    # Source information
    source_domain: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    crawled_at: Optional[datetime] = None
    
    # Analytics
    view_count: int = 0
    question_generation_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Tags and categories
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    
    # Vector database information
    vector_db_id: Optional[str] = None
    embedding_model: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            'content_id': self.content_id,
            'url': self.url,
            'title': self.title,
            'summary': self.summary,
            'key_points': self.key_points,
            'questions': self.questions,
            'word_count': self.word_count,
            'reading_time_minutes': self.reading_time_minutes,
            'language': self.language,
            'content_type': self.content_type,
            'processed_at': self.processed_at,
            'processing_version': self.processing_version,
            'llm_provider': self.llm_provider,
            'llm_model': self.llm_model,
            'source_domain': self.source_domain,
            'author': self.author,
            'published_date': self.published_date,
            'crawled_at': self.crawled_at,
            'view_count': self.view_count,
            'question_generation_count': self.question_generation_count,
            'last_accessed': self.last_accessed,
            'tags': self.tags,
            'categories': self.categories,
            'vector_db_id': self.vector_db_id,
            'embedding_model': self.embedding_model,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentMetadata':
        """Create instance from dictionary."""
        return cls(
            content_id=data['content_id'],
            url=data['url'],
            title=data['title'],
            summary=data['summary'],
            key_points=data.get('key_points', []),
            questions=data.get('questions', []),
            word_count=data.get('word_count'),
            reading_time_minutes=data.get('reading_time_minutes'),
            language=data.get('language', 'en'),
            content_type=data.get('content_type', 'article'),
            processed_at=data.get('processed_at', datetime.utcnow()),
            processing_version=data.get('processing_version', '1.0'),
            llm_provider=data.get('llm_provider'),
            llm_model=data.get('llm_model'),
            source_domain=data.get('source_domain'),
            author=data.get('author'),
            published_date=data.get('published_date'),
            crawled_at=data.get('crawled_at'),
            view_count=data.get('view_count', 0),
            question_generation_count=data.get('question_generation_count', 0),
            last_accessed=data.get('last_accessed'),
            tags=data.get('tags', []),
            categories=data.get('categories', []),
            vector_db_id=data.get('vector_db_id'),
            embedding_model=data.get('embedding_model'),
            metadata=data.get('metadata', {})
        )


@dataclass
class UserInteraction:
    """
    User interaction tracking for analytics and personalization.
    
    Tracks how users interact with content including views, questions,
    and other engagement metrics.
    """
    
    # Core identifiers
    interaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_id: str = ""
    user_id: Optional[str] = None  # For future user system
    session_id: Optional[str] = None
    
    # Interaction details
    interaction_type: InteractionType = InteractionType.VIEW
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Context information
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    referrer: Optional[str] = None
    
    # Interaction-specific data
    question_id: Optional[str] = None
    answer_provided: Optional[str] = None
    time_spent_seconds: Optional[int] = None
    scroll_percentage: Optional[float] = None
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            'interaction_id': self.interaction_id,
            'content_id': self.content_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'interaction_type': self.interaction_type.value,
            'timestamp': self.timestamp,
            'user_agent': self.user_agent,
            'ip_address': self.ip_address,
            'referrer': self.referrer,
            'question_id': self.question_id,
            'answer_provided': self.answer_provided,
            'time_spent_seconds': self.time_spent_seconds,
            'scroll_percentage': self.scroll_percentage,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserInteraction':
        """Create instance from dictionary."""
        return cls(
            interaction_id=data.get('interaction_id', str(uuid.uuid4())),
            content_id=data['content_id'],
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            interaction_type=InteractionType(data.get('interaction_type', 'view')),
            timestamp=data.get('timestamp', datetime.utcnow()),
            user_agent=data.get('user_agent'),
            ip_address=data.get('ip_address'),
            referrer=data.get('referrer'),
            question_id=data.get('question_id'),
            answer_provided=data.get('answer_provided'),
            time_spent_seconds=data.get('time_spent_seconds'),
            scroll_percentage=data.get('scroll_percentage'),
            metadata=data.get('metadata', {})
        )


@dataclass
class SearchAnalytics:
    """
    Search analytics for tracking search patterns and performance.
    
    Helps understand what users are searching for and how effective
    the search functionality is.
    """
    
    # Core identifiers
    search_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    
    # Search results
    result_count: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    search_time_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # User context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Search parameters
    search_type: str = "similarity"  # similarity, keyword, hybrid
    embedding_model: Optional[str] = None
    similarity_threshold: Optional[float] = None
    max_results: int = 10
    
    # User interaction with results
    clicked_results: List[str] = field(default_factory=list)  # content_ids
    result_click_positions: List[int] = field(default_factory=list)
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            'search_id': self.search_id,
            'query': self.query,
            'result_count': self.result_count,
            'results': self.results,
            'search_time_ms': self.search_time_ms,
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'user_agent': self.user_agent,
            'search_type': self.search_type,
            'embedding_model': self.embedding_model,
            'similarity_threshold': self.similarity_threshold,
            'max_results': self.max_results,
            'clicked_results': self.clicked_results,
            'result_click_positions': self.result_click_positions,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchAnalytics':
        """Create instance from dictionary."""
        return cls(
            search_id=data.get('search_id', str(uuid.uuid4())),
            query=data['query'],
            result_count=data.get('result_count', 0),
            results=data.get('results', []),
            search_time_ms=data.get('search_time_ms'),
            timestamp=data.get('timestamp', datetime.utcnow()),
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            user_agent=data.get('user_agent'),
            search_type=data.get('search_type', 'similarity'),
            embedding_model=data.get('embedding_model'),
            similarity_threshold=data.get('similarity_threshold'),
            max_results=data.get('max_results', 10),
            clicked_results=data.get('clicked_results', []),
            result_click_positions=data.get('result_click_positions', []),
            metadata=data.get('metadata', {})
        )


@dataclass
class ProcessingJob:
    """
    Processing job tracking for content pipeline operations.
    
    Tracks the status and progress of content processing jobs including
    crawling, summarization, question generation, and vector indexing.
    """
    
    # Core identifiers
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_id: Optional[str] = None
    url: Optional[str] = None
    
    # Job details
    job_type: str = ""  # crawl, summarize, generate_questions, index_vectors
    status: ProcessingStatus = ProcessingStatus.PENDING
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress tracking
    progress_percentage: float = 0.0
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    
    # Results and errors
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # Processing configuration
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    processing_options: Dict[str, Any] = field(default_factory=dict)
    
    # Resource usage
    processing_time_seconds: Optional[float] = None
    tokens_used: Optional[int] = None
    api_calls_made: Optional[int] = None
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            'job_id': self.job_id,
            'content_id': self.content_id,
            'url': self.url,
            'job_type': self.job_type,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'progress_percentage': self.progress_percentage,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'result': self.result,
            'error_message': self.error_message,
            'error_traceback': self.error_traceback,
            'llm_provider': self.llm_provider,
            'llm_model': self.llm_model,
            'processing_options': self.processing_options,
            'processing_time_seconds': self.processing_time_seconds,
            'tokens_used': self.tokens_used,
            'api_calls_made': self.api_calls_made,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingJob':
        """Create instance from dictionary."""
        return cls(
            job_id=data.get('job_id', str(uuid.uuid4())),
            content_id=data.get('content_id'),
            url=data.get('url'),
            job_type=data['job_type'],
            status=ProcessingStatus(data.get('status', 'pending')),
            created_at=data.get('created_at', datetime.utcnow()),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            progress_percentage=data.get('progress_percentage', 0.0),
            current_step=data.get('current_step'),
            total_steps=data.get('total_steps'),
            result=data.get('result'),
            error_message=data.get('error_message'),
            error_traceback=data.get('error_traceback'),
            llm_provider=data.get('llm_provider'),
            llm_model=data.get('llm_model'),
            processing_options=data.get('processing_options', {}),
            processing_time_seconds=data.get('processing_time_seconds'),
            tokens_used=data.get('tokens_used'),
            api_calls_made=data.get('api_calls_made'),
            metadata=data.get('metadata', {})
        )
    
    def update_progress(self, percentage: float, step: Optional[str] = None) -> None:
        """Update job progress."""
        self.progress_percentage = min(100.0, max(0.0, percentage))
        if step:
            self.current_step = step
    
    def mark_started(self) -> None:
        """Mark job as started."""
        self.status = ProcessingStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def mark_completed(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark job as completed."""
        self.status = ProcessingStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100.0
        if result:
            self.result = result
        
        if self.started_at:
            self.processing_time_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()
    
    def mark_failed(self, error_message: str, error_traceback: Optional[str] = None) -> None:
        """Mark job as failed."""
        self.status = ProcessingStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_traceback = error_traceback
        
        if self.started_at:
            self.processing_time_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()
