"""
Vector search service implementation.

This module provides the main service for indexing content and performing
similarity searches using embeddings and vector storage.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime

from ..core.interfaces import IVectorSearchService, IEmbeddingProvider, IVectorStore
from ..models.vector_models import (
    VectorDocument, VectorMetadata, SearchRequest, SearchResult, EmbeddingRequest
)
from ..services.embedding_service import EmbeddingService
from ..storage.in_memory_store import InMemoryVectorStore
from ..utils.exceptions import VectorSearchError, ResourceNotFoundError
from ..utils.text_processing import TextPreprocessor

logger = logging.getLogger(__name__)


class VectorSearchService(IVectorSearchService):
    """
    High-level vector search service implementation.
    
    Combines embedding generation and vector storage to provide
    end-to-end content indexing and similarity search capabilities.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: IVectorStore,
        enable_preprocessing: bool = True
    ):
        """
        Initialize vector search service.
        
        Args:
            embedding_service: Service for generating embeddings
            vector_store: Vector storage backend
            enable_preprocessing: Whether to enable text preprocessing
        """
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._preprocessor = TextPreprocessor() if enable_preprocessing else None
        self._initialized = False
        
        logger.info("Initialized vector search service")
    
    async def initialize(self) -> None:
        """Initialize the vector search service."""
        if not self._initialized:
            await self._vector_store.initialize()
            self._initialized = True
            logger.info("Vector search service initialized")
    
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
        try:
            await self.initialize()
            
            # Validate input
            if not content.strip():
                raise VectorSearchError(
                    "Content cannot be empty",
                    search_type="index_content"
                )
            
            # Preprocess content if enabled
            processed_content = content
            if self._preprocessor:
                processed_content = self._preprocessor.preprocess(content)
            
            # Generate embedding
            embedding = await self._embedding_service.generate_embedding(
                text=processed_content,
                preprocess=False,  # Already preprocessed
                normalize=True
            )
            
            # Update metadata with embedding information
            primary_provider = self._embedding_service.get_primary_provider()
            if primary_provider:
                metadata.embedding_provider = primary_provider.provider_name
                metadata.embedding_model = primary_provider.model_name
            
            metadata.indexed_at = datetime.now()
            metadata.updated_at = datetime.now()
            
            # Create vector document
            vector_doc = VectorDocument(
                content=content,  # Store original content
                embedding=embedding,
                metadata=metadata,
                document_id=content_id
            )
            
            # Store in vector database
            doc_id = await self._vector_store.add_document(vector_doc)
            
            logger.info(f"Indexed content with ID: {doc_id}")
            return doc_id
            
        except VectorSearchError:
            raise
        except Exception as e:
            raise VectorSearchError(
                f"Failed to index content: {str(e)}",
                search_type="index_content",
                cause=e
            )
    
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
        try:
            await self.initialize()
            
            if not content_items:
                return []
            
            # Validate and preprocess content
            processed_items = []
            for content, metadata, content_id in content_items:
                if not content.strip():
                    raise VectorSearchError(
                        "Content cannot be empty in batch",
                        search_type="index_content_batch"
                    )
                
                processed_content = content
                if self._preprocessor:
                    processed_content = self._preprocessor.preprocess(content)
                
                processed_items.append((content, processed_content, metadata, content_id))
            
            # Generate embeddings in batch
            texts_to_embed = [item[1] for item in processed_items]  # processed content
            embeddings = await self._embedding_service.generate_embeddings_batch(
                texts=texts_to_embed,
                preprocess=False,  # Already preprocessed
                normalize=True
            )
            
            # Create vector documents
            vector_documents = []
            primary_provider = self._embedding_service.get_primary_provider()
            
            for i, (original_content, _, metadata, content_id) in enumerate(processed_items):
                # Update metadata
                if primary_provider:
                    metadata.embedding_provider = primary_provider.provider_name
                    metadata.embedding_model = primary_provider.model_name
                
                metadata.indexed_at = datetime.now()
                metadata.updated_at = datetime.now()
                
                vector_doc = VectorDocument(
                    content=original_content,  # Store original content
                    embedding=embeddings[i],
                    metadata=metadata,
                    document_id=content_id
                )
                vector_documents.append(vector_doc)
            
            # Store in vector database
            doc_ids = await self._vector_store.add_documents_batch(vector_documents)
            
            logger.info(f"Indexed {len(doc_ids)} content items in batch")
            return doc_ids
            
        except VectorSearchError:
            raise
        except Exception as e:
            raise VectorSearchError(
                f"Failed to index content batch: {str(e)}",
                search_type="index_content_batch",
                cause=e
            )
    
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
        try:
            await self.initialize()
            
            # Validate input
            if not query.strip():
                raise VectorSearchError(
                    "Query cannot be empty",
                    query=query,
                    search_type="similarity_search"
                )
            
            # Preprocess query
            processed_query = query
            if self._preprocessor:
                processed_query = self._preprocessor.preprocess(query)
            
            # Generate query embedding
            query_embedding = await self._embedding_service.generate_embedding(
                text=processed_query,
                preprocess=False,  # Already preprocessed
                normalize=True
            )
            
            # Perform similarity search
            search_results = await self._vector_store.similarity_search(
                query_embedding=query_embedding,
                limit=limit,
                metadata_filter=metadata_filter,
                similarity_threshold=similarity_threshold
            )
            
            # Convert to SearchResult objects
            results = []
            for i, (document, similarity_score) in enumerate(search_results):
                result = SearchResult(
                    document_id=document.document_id,
                    content=document.content,
                    metadata=document.metadata,
                    similarity_score=similarity_score,
                    rank=i + 1
                )
                results.append(result)
            
            logger.debug(f"Found {len(results)} similar documents for query")
            return results
            
        except VectorSearchError:
            raise
        except Exception as e:
            raise VectorSearchError(
                f"Failed to search similar content: {str(e)}",
                query=query,
                search_type="similarity_search",
                filter_criteria=metadata_filter,
                cause=e
            )
    
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
        try:
            await self.initialize()
            
            # First, find the document with the given URL
            url_filter = {"url": url}
            url_results = await self._vector_store.similarity_search(
                query_embedding=np.zeros(1),  # Dummy embedding, we're filtering by metadata
                limit=1,
                metadata_filter=url_filter
            )
            
            if not url_results:
                raise ResourceNotFoundError(
                    f"No content found for URL: {url}",
                    resource_type="document",
                    resource_id=url
                )
            
            # Use the found document's embedding for similarity search
            source_document, _ = url_results[0]
            
            # Search for similar content (excluding the source document)
            all_results = await self._vector_store.similarity_search(
                query_embedding=source_document.embedding,
                limit=limit + 1,  # Get one extra to exclude source
                similarity_threshold=similarity_threshold
            )
            
            # Filter out the source document and convert to SearchResult
            results = []
            for i, (document, similarity_score) in enumerate(all_results):
                if document.document_id != source_document.document_id:
                    result = SearchResult(
                        document_id=document.document_id,
                        content=document.content,
                        metadata=document.metadata,
                        similarity_score=similarity_score,
                        rank=len(results) + 1
                    )
                    results.append(result)
                    
                    if len(results) >= limit:
                        break
            
            logger.debug(f"Found {len(results)} documents similar to URL: {url}")
            return results
            
        except VectorSearchError:
            raise
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise VectorSearchError(
                f"Failed to search by URL: {str(e)}",
                search_type="search_by_url",
                filter_criteria={"url": url},
                cause=e
            )
    
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
        try:
            await self.initialize()
            
            # Search for document with the given URL
            url_filter = {"url": url}
            results = await self._vector_store.similarity_search(
                query_embedding=np.zeros(1),  # Dummy embedding, we're filtering by metadata
                limit=1,
                metadata_filter=url_filter
            )
            
            if not results:
                return None
            
            document, _ = results[0]
            return SearchResult(
                document_id=document.document_id,
                content=document.content,
                metadata=document.metadata,
                similarity_score=1.0,  # Exact match
                rank=1
            )
            
        except Exception as e:
            raise VectorSearchError(
                f"Failed to get content by URL: {str(e)}",
                search_type="get_by_url",
                filter_criteria={"url": url},
                cause=e
            )
    
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
        try:
            await self.initialize()
            
            # Get existing document
            document = await self._vector_store.get_document(document_id)
            if not document:
                return False
            
            # Update metadata
            for key, value in metadata_updates.items():
                if hasattr(document.metadata, key):
                    setattr(document.metadata, key, value)
                else:
                    document.metadata.custom_fields[key] = value
            
            document.metadata.updated_at = datetime.now()
            
            # Update in store
            success = await self._vector_store.update_document(document_id, document)
            
            if success:
                logger.debug(f"Updated metadata for document {document_id}")
            
            return success
            
        except Exception as e:
            raise VectorSearchError(
                f"Failed to update content metadata: {str(e)}",
                search_type="update_metadata",
                cause=e
            )
    
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
        try:
            await self.initialize()
            
            success = await self._vector_store.delete_document(document_id)
            
            if success:
                logger.info(f"Deleted document {document_id}")
            
            return success
            
        except Exception as e:
            raise VectorSearchError(
                f"Failed to delete content: {str(e)}",
                search_type="delete_content",
                cause=e
            )
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed content.
        
        Returns:
            Dictionary containing statistics
            
        Raises:
            VectorSearchError: If statistics retrieval fails
        """
        try:
            await self.initialize()
            
            # Get basic document count
            document_count = await self._vector_store.count_documents()
            
            # Get provider statistics
            provider_stats = self._embedding_service.get_provider_stats()
            
            # Get store-specific statistics if available
            store_stats = {}
            if hasattr(self._vector_store, 'get_statistics'):
                store_stats = self._vector_store.get_statistics()
            
            return {
                'document_count': document_count,
                'vector_store': {
                    'type': self._vector_store.store_name,
                    'is_persistent': self._vector_store.is_persistent,
                    **store_stats
                },
                'embedding_providers': provider_stats,
                'available_providers': self._embedding_service.get_available_providers(),
                'service_initialized': self._initialized
            }
            
        except Exception as e:
            raise VectorSearchError(
                f"Failed to get statistics: {str(e)}",
                search_type="get_statistics",
                cause=e
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of the service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            health_status = {
                'service_healthy': True,
                'vector_store_healthy': False,
                'embedding_providers': {},
                'errors': []
            }
            
            # Check vector store health
            try:
                store_healthy = await self._vector_store.health_check()
                health_status['vector_store_healthy'] = store_healthy
                if not store_healthy:
                    health_status['errors'].append("Vector store health check failed")
            except Exception as e:
                health_status['errors'].append(f"Vector store error: {str(e)}")
            
            # Check embedding provider health
            try:
                provider_health = await self._embedding_service.health_check_all_providers()
                health_status['embedding_providers'] = provider_health
                
                if not any(provider_health.values()):
                    health_status['errors'].append("No healthy embedding providers")
            except Exception as e:
                health_status['errors'].append(f"Embedding service error: {str(e)}")
            
            # Overall health
            health_status['service_healthy'] = (
                health_status['vector_store_healthy'] and
                any(health_status['embedding_providers'].values()) and
                len(health_status['errors']) == 0
            )
            
            return health_status
            
        except Exception as e:
            return {
                'service_healthy': False,
                'error': str(e)
            }
    
    @classmethod
    async def create_default_service(
        cls,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        use_sentence_transformers: bool = True,
        vector_store: Optional[IVectorStore] = None
    ) -> 'VectorSearchService':
        """
        Create a default vector search service with common configuration.
        
        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            use_sentence_transformers: Whether to use sentence transformers
            vector_store: Custom vector store (uses in-memory if None)
            
        Returns:
            Configured vector search service
        """
        # Create embedding service
        embedding_service = EmbeddingService.create_default_service(
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key,
            use_sentence_transformers=use_sentence_transformers
        )
        
        # Create vector store if not provided
        if vector_store is None:
            vector_store = InMemoryVectorStore()
        
        # Create and initialize service
        service = cls(
            embedding_service=embedding_service,
            vector_store=vector_store
        )
        
        await service.initialize()
        return service
