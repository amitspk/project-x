"""
Data models for vector database operations.

This module defines the core data structures used throughout the vector database
system for embeddings, documents, search requests, and results.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum
import numpy as np


class EmbeddingModel(Enum):
    """Supported embedding models."""
    OPENAI_TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"
    OPENAI_TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    OPENAI_TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    ANTHROPIC_CLAUDE_EMBEDDING = "claude-embedding"
    SENTENCE_TRANSFORMERS_ALL_MPNET = "all-MiniLM-L6-v2"
    SENTENCE_TRANSFORMERS_ALL_DISTILBERT = "all-distilroberta-v1"


class VectorStoreType(Enum):
    """Supported vector store types."""
    CHROMA = "chroma"
    FAISS = "faiss"
    PINECONE = "pinecone"
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"
    IN_MEMORY = "in_memory"


@dataclass
class VectorMetadata:
    """
    Metadata associated with vector documents.
    
    Contains information about the original content, processing details,
    and custom fields for filtering and retrieval.
    """
    
    # Content identification
    url: Optional[str] = None
    title: Optional[str] = None
    content_id: Optional[str] = None
    content_hash: Optional[str] = None
    
    # Content classification
    content_type: str = "article"
    language: str = "en"
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    
    # Content metrics
    word_count: int = 0
    character_count: int = 0
    estimated_reading_time: int = 0  # minutes
    
    # Processing metadata
    indexed_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    embedding_model: Optional[str] = None
    embedding_provider: Optional[str] = None
    
    # Source information
    source: str = "unknown"
    source_path: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    
    # Quality metrics
    confidence_score: float = 0.0
    quality_score: float = 0.0
    
    # Custom fields for extensibility
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        
        # Convert datetime objects to ISO strings
        data['indexed_at'] = self.indexed_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        
        if self.published_date:
            data['published_date'] = self.published_date.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorMetadata':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        if data.get('indexed_at'):
            data['indexed_at'] = datetime.fromisoformat(data['indexed_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('published_date'):
            data['published_date'] = datetime.fromisoformat(data['published_date'])
        
        return cls(**data)
    
    def add_tags(self, tags: List[str]) -> None:
        """Add tags to metadata."""
        existing_tags = set(self.tags)
        new_tags = set(tags)
        self.tags = list(existing_tags.union(new_tags))
        self.updated_at = datetime.now()
    
    def add_categories(self, categories: List[str]) -> None:
        """Add categories to metadata."""
        existing_categories = set(self.categories)
        new_categories = set(categories)
        self.categories = list(existing_categories.union(new_categories))
        self.updated_at = datetime.now()
    
    def update_custom_field(self, key: str, value: Any) -> None:
        """Update a custom field."""
        self.custom_fields[key] = value
        self.updated_at = datetime.now()


@dataclass
class EmbeddingRequest:
    """
    Request for generating embeddings from text content.
    
    Contains the text to embed along with optional parameters
    for controlling the embedding generation process.
    """
    
    text: str
    model: Optional[EmbeddingModel] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    normalize: bool = True
    
    # Request metadata
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.text.strip():
            raise ValueError("Text content cannot be empty")
        
        if self.request_id is None:
            self.request_id = self._generate_request_id()
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        content_hash = hashlib.md5(self.text.encode('utf-8')).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"emb_{timestamp}_{content_hash}"
    
    def get_text_chunks(self) -> List[str]:
        """Split text into chunks if chunk_size is specified."""
        if not self.chunk_size:
            return [self.text]
        
        chunks = []
        overlap = self.chunk_overlap or 0
        
        words = self.text.split()
        start = 0
        
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk = ' '.join(words[start:end])
            chunks.append(chunk)
            
            if end >= len(words):
                break
            
            start = end - overlap
        
        return chunks


@dataclass
class VectorDocument:
    """
    Document containing content, embedding, and metadata for vector storage.
    
    Represents a complete document with its vector representation
    and associated metadata for storage and retrieval.
    """
    
    content: str
    embedding: np.ndarray
    metadata: VectorMetadata
    document_id: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.content.strip():
            raise ValueError("Document content cannot be empty")
        
        if self.embedding.size == 0:
            raise ValueError("Embedding cannot be empty")
        
        if self.document_id is None:
            self.document_id = self._generate_document_id()
        
        # Update metadata with content metrics
        self._update_content_metrics()
    
    def _generate_document_id(self) -> str:
        """Generate unique document ID."""
        content_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()[:16]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"doc_{timestamp}_{content_hash}"
    
    def _update_content_metrics(self) -> None:
        """Update content metrics in metadata."""
        self.metadata.word_count = len(self.content.split())
        self.metadata.character_count = len(self.content)
        self.metadata.estimated_reading_time = max(1, self.metadata.word_count // 200)
        
        if not self.metadata.content_hash:
            self.metadata.content_hash = hashlib.sha256(
                self.content.encode('utf-8')
            ).hexdigest()[:16]
    
    def to_dict(self, include_embedding: bool = True) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Args:
            include_embedding: Whether to include the embedding vector
            
        Returns:
            Dictionary representation of the document
        """
        data = {
            'document_id': self.document_id,
            'content': self.content,
            'metadata': self.metadata.to_dict()
        }
        
        if include_embedding:
            data['embedding'] = self.embedding.tolist()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorDocument':
        """Create VectorDocument from dictionary."""
        metadata = VectorMetadata.from_dict(data.get('metadata', {}))
        embedding = np.array(data['embedding'])
        
        return cls(
            content=data['content'],
            embedding=embedding,
            metadata=metadata,
            document_id=data.get('document_id')
        )
    
    def update_content(self, new_content: str) -> None:
        """Update document content and regenerate metrics."""
        self.content = new_content
        self._update_content_metrics()
        self.metadata.updated_at = datetime.now()
    
    def update_embedding(self, new_embedding: np.ndarray) -> None:
        """Update document embedding."""
        if new_embedding.size == 0:
            raise ValueError("New embedding cannot be empty")
        
        self.embedding = new_embedding
        self.metadata.updated_at = datetime.now()
    
    def get_similarity_score(self, other_embedding: np.ndarray) -> float:
        """
        Calculate cosine similarity with another embedding.
        
        Args:
            other_embedding: Embedding to compare with
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        # Normalize embeddings
        norm_self = self.embedding / np.linalg.norm(self.embedding)
        norm_other = other_embedding / np.linalg.norm(other_embedding)
        
        # Calculate cosine similarity
        similarity = np.dot(norm_self, norm_other)
        
        # Ensure result is between 0 and 1
        return max(0.0, min(1.0, (similarity + 1) / 2))


@dataclass
class SearchRequest:
    """
    Request for similarity search in vector database.
    
    Contains query parameters and filters for performing
    similarity search operations.
    """
    
    query: str
    limit: int = 10
    similarity_threshold: Optional[float] = None
    metadata_filter: Optional[Dict[str, Any]] = None
    
    # Search options
    include_content: bool = True
    include_metadata: bool = True
    include_similarity_score: bool = True
    
    # Request metadata
    request_id: Optional[str] = None
    requested_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.query.strip():
            raise ValueError("Search query cannot be empty")
        
        if self.limit <= 0:
            raise ValueError("Search limit must be positive")
        
        if self.similarity_threshold is not None:
            if not 0.0 <= self.similarity_threshold <= 1.0:
                raise ValueError("Similarity threshold must be between 0 and 1")
        
        if self.request_id is None:
            self.request_id = self._generate_request_id()
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        query_hash = hashlib.md5(self.query.encode('utf-8')).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"search_{timestamp}_{query_hash}"


@dataclass
class SearchResult:
    """
    Result from similarity search operation.
    
    Contains the matched document information along with
    similarity score and search metadata.
    """
    
    document_id: str
    content: Optional[str] = None
    metadata: Optional[VectorMetadata] = None
    similarity_score: Optional[float] = None
    
    # Result metadata
    rank: Optional[int] = None
    search_request_id: Optional[str] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            'document_id': self.document_id,
            'rank': self.rank,
            'similarity_score': self.similarity_score,
            'search_request_id': self.search_request_id,
            'retrieved_at': self.retrieved_at.isoformat()
        }
        
        if self.content is not None:
            data['content'] = self.content
        
        if self.metadata is not None:
            data['metadata'] = self.metadata.to_dict()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create SearchResult from dictionary."""
        metadata = None
        if data.get('metadata'):
            metadata = VectorMetadata.from_dict(data['metadata'])
        
        retrieved_at = datetime.now()
        if data.get('retrieved_at'):
            retrieved_at = datetime.fromisoformat(data['retrieved_at'])
        
        return cls(
            document_id=data['document_id'],
            content=data.get('content'),
            metadata=metadata,
            similarity_score=data.get('similarity_score'),
            rank=data.get('rank'),
            search_request_id=data.get('search_request_id'),
            retrieved_at=retrieved_at
        )
    
    def get_url(self) -> Optional[str]:
        """Get URL from metadata if available."""
        return self.metadata.url if self.metadata else None
    
    def get_title(self) -> Optional[str]:
        """Get title from metadata if available."""
        return self.metadata.title if self.metadata else None
    
    def get_tags(self) -> List[str]:
        """Get tags from metadata if available."""
        return self.metadata.tags if self.metadata else []
    
    def matches_filter(self, filter_dict: Dict[str, Any]) -> bool:
        """
        Check if this result matches the given filter criteria.
        
        Args:
            filter_dict: Dictionary of filter criteria
            
        Returns:
            True if result matches all filter criteria
        """
        if not self.metadata:
            return False
        
        for key, expected_value in filter_dict.items():
            if key == 'tags':
                # Check if any expected tags are present
                if isinstance(expected_value, list):
                    if not any(tag in self.metadata.tags for tag in expected_value):
                        return False
                else:
                    if expected_value not in self.metadata.tags:
                        return False
            elif key == 'categories':
                # Check if any expected categories are present
                if isinstance(expected_value, list):
                    if not any(cat in self.metadata.categories for cat in expected_value):
                        return False
                else:
                    if expected_value not in self.metadata.categories:
                        return False
            elif hasattr(self.metadata, key):
                actual_value = getattr(self.metadata, key)
                if actual_value != expected_value:
                    return False
            elif key in self.metadata.custom_fields:
                if self.metadata.custom_fields[key] != expected_value:
                    return False
            else:
                return False
        
        return True
