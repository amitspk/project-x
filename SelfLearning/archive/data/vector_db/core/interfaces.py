"""
Core interfaces for the vector database module.

This module defines the abstract interfaces that all vector database components
must implement, ensuring consistency and enabling dependency injection.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np

from ..models.vector_models import (
    VectorDocument,
    EmbeddingRequest,
    SearchRequest,
    SearchResult,
    VectorMetadata
)


class IEmbeddingProvider(ABC):
    """
    Abstract interface for embedding providers.
    
    Supports multiple embedding models and providers (OpenAI, Anthropic, local models).
    Provides consistent interface for generating embeddings from text content.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of the embedding provider."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the name of the embedding model."""
        pass
    
    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        pass
    
    @abstractmethod
    async def generate_embedding(self, request: EmbeddingRequest) -> np.ndarray:
        """
        Generate embedding for a single text input.
        
        Args:
            request: Embedding request containing text and optional parameters
            
        Returns:
            Numpy array containing the embedding vector
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass
    
    @abstractmethod
    async def generate_embeddings_batch(
        self, 
        requests: List[EmbeddingRequest]
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple text inputs in batch.
        
        Args:
            requests: List of embedding requests
            
        Returns:
            List of numpy arrays containing embedding vectors
            
        Raises:
            EmbeddingError: If batch embedding generation fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the embedding provider is healthy and accessible.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass


class IVectorStore(ABC):
    """
    Abstract interface for vector storage backends.
    
    Supports multiple vector databases (Chroma, FAISS, Pinecone, etc.)
    with consistent CRUD operations and similarity search capabilities.
    """
    
    @property
    @abstractmethod
    def store_name(self) -> str:
        """Get the name of the vector store."""
        pass
    
    @property
    @abstractmethod
    def is_persistent(self) -> bool:
        """Check if this store persists data between sessions."""
        pass
    
    @abstractmethod
    async def initialize(self, **kwargs) -> None:
        """
        Initialize the vector store with configuration.
        
        Args:
            **kwargs: Store-specific configuration parameters
            
        Raises:
            VectorStoreError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def add_document(self, document: VectorDocument) -> str:
        """
        Add a single document with its embedding to the store.
        
        Args:
            document: Vector document containing content, embedding, and metadata
            
        Returns:
            Document ID assigned by the store
            
        Raises:
            VectorStoreError: If document addition fails
        """
        pass
    
    @abstractmethod
    async def add_documents_batch(self, documents: List[VectorDocument]) -> List[str]:
        """
        Add multiple documents to the store in batch.
        
        Args:
            documents: List of vector documents
            
        Returns:
            List of document IDs assigned by the store
            
        Raises:
            VectorStoreError: If batch addition fails
        """
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """
        Retrieve a document by its ID.
        
        Args:
            document_id: Unique document identifier
            
        Returns:
            Vector document if found, None otherwise
            
        Raises:
            VectorStoreError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def update_document(self, document_id: str, document: VectorDocument) -> bool:
        """
        Update an existing document.
        
        Args:
            document_id: Document ID to update
            document: Updated vector document
            
        Returns:
            True if update successful, False if document not found
            
        Raises:
            VectorStoreError: If update fails
        """
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document by its ID.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if deletion successful, False if document not found
            
        Raises:
            VectorStoreError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Tuple[VectorDocument, float]]:
        """
        Perform similarity search using query embedding.
        
        Args:
            query_embedding: Query vector for similarity search
            limit: Maximum number of results to return
            metadata_filter: Optional metadata filters
            similarity_threshold: Minimum similarity score threshold
            
        Returns:
            List of tuples containing (document, similarity_score)
            
        Raises:
            VectorStoreError: If search fails
        """
        pass
    
    @abstractmethod
    async def count_documents(self, metadata_filter: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents in the store.
        
        Args:
            metadata_filter: Optional metadata filters
            
        Returns:
            Number of documents matching the filter
            
        Raises:
            VectorStoreError: If count operation fails
        """
        pass
    
    @abstractmethod
    async def clear_store(self) -> None:
        """
        Clear all documents from the store.
        
        Raises:
            VectorStoreError: If clear operation fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the vector store is healthy and accessible.
        
        Returns:
            True if store is healthy, False otherwise
        """
        pass


class IVectorSearchService(ABC):
    """
    High-level interface for vector search operations.
    
    Combines embedding generation and vector storage for end-to-end
    content indexing and similarity search capabilities.
    """
    
    @abstractmethod
    async def index_content(
        self,
        content: str,
        metadata: VectorMetadata,
        content_id: Optional[str] = None
    ) -> str:
        """
        Index content by generating embeddings and storing in vector database.
        
        Args:
            content: Text content to index
            metadata: Metadata associated with the content
            content_id: Optional custom content ID
            
        Returns:
            Document ID in the vector store
            
        Raises:
            VectorSearchError: If indexing fails
        """
        pass
    
    @abstractmethod
    async def index_content_batch(
        self,
        content_items: List[Tuple[str, VectorMetadata, Optional[str]]]
    ) -> List[str]:
        """
        Index multiple content items in batch.
        
        Args:
            content_items: List of (content, metadata, optional_id) tuples
            
        Returns:
            List of document IDs in the vector store
            
        Raises:
            VectorSearchError: If batch indexing fails
        """
        pass
    
    @abstractmethod
    async def search_similar_content(
        self,
        query: str,
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Search for content similar to the query text.
        
        Args:
            query: Query text to search for
            limit: Maximum number of results
            metadata_filter: Optional metadata filters
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of search results with content and metadata
            
        Raises:
            VectorSearchError: If search fails
        """
        pass
    
    @abstractmethod
    async def search_by_url(
        self,
        url: str,
        limit: int = 10,
        similarity_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Find content similar to content from a specific URL.
        
        Args:
            url: URL to find similar content for
            limit: Maximum number of results
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of search results
            
        Raises:
            VectorSearchError: If search fails
        """
        pass
    
    @abstractmethod
    async def get_content_by_url(self, url: str) -> Optional[SearchResult]:
        """
        Retrieve content metadata by URL.
        
        Args:
            url: URL to search for
            
        Returns:
            Search result if found, None otherwise
            
        Raises:
            VectorSearchError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def update_content_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """
        Update metadata for existing content.
        
        Args:
            document_id: Document ID to update
            metadata_updates: Metadata fields to update
            
        Returns:
            True if update successful, False if document not found
            
        Raises:
            VectorSearchError: If update fails
        """
        pass
    
    @abstractmethod
    async def delete_content(self, document_id: str) -> bool:
        """
        Delete content from the vector store.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if deletion successful, False if document not found
            
        Raises:
            VectorSearchError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed content.
        
        Returns:
            Dictionary containing statistics (document count, etc.)
            
        Raises:
            VectorSearchError: If statistics retrieval fails
        """
        pass
