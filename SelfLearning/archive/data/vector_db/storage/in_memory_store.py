"""
In-memory vector store implementation.

This module provides a simple in-memory vector store for development,
testing, and small-scale applications that don't require persistence.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime

from ..core.interfaces import IVectorStore
from ..models.vector_models import VectorDocument, VectorMetadata
from ..utils.exceptions import VectorStoreError, ResourceNotFoundError
from ..utils.similarity_metrics import cosine_similarity, batch_cosine_similarity, top_k_similar

logger = logging.getLogger(__name__)


class InMemoryVectorStore(IVectorStore):
    """
    In-memory vector store implementation.
    
    Stores vectors and metadata in memory with basic similarity search capabilities.
    Suitable for development, testing, and small datasets that don't require persistence.
    """
    
    def __init__(self, embedding_dimension: Optional[int] = None):
        """
        Initialize in-memory vector store.
        
        Args:
            embedding_dimension: Expected dimension of embeddings (optional)
        """
        self._embedding_dimension = embedding_dimension
        self._documents: Dict[str, VectorDocument] = {}
        self._embeddings: Dict[str, np.ndarray] = {}
        self._metadata: Dict[str, VectorMetadata] = {}
        self._initialized = False
        
        logger.info("Initialized in-memory vector store")
    
    @property
    def store_name(self) -> str:
        """Get the name of the vector store."""
        return "in_memory"
    
    @property
    def is_persistent(self) -> bool:
        """Check if this store persists data between sessions."""
        return False
    
    async def initialize(self, **kwargs) -> None:
        """
        Initialize the vector store with configuration.
        
        Args:
            **kwargs: Configuration parameters (embedding_dimension, etc.)
            
        Raises:
            VectorStoreError: If initialization fails
        """
        try:
            # Update embedding dimension if provided
            if 'embedding_dimension' in kwargs:
                self._embedding_dimension = kwargs['embedding_dimension']
            
            self._initialized = True
            logger.info("In-memory vector store initialized successfully")
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize in-memory vector store: {str(e)}",
                store_type=self.store_name,
                operation="initialize",
                cause=e
            )
    
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
        try:
            if not self._initialized:
                await self.initialize()
            
            # Validate embedding dimension
            if self._embedding_dimension is not None:
                if document.embedding.shape[0] != self._embedding_dimension:
                    raise VectorStoreError(
                        f"Embedding dimension mismatch: expected {self._embedding_dimension}, "
                        f"got {document.embedding.shape[0]}",
                        store_type=self.store_name,
                        operation="add_document"
                    )
            else:
                # Set dimension from first document
                self._embedding_dimension = document.embedding.shape[0]
            
            # Generate document ID if not provided
            doc_id = document.document_id
            if not doc_id:
                doc_id = self._generate_document_id()
                document.document_id = doc_id
            
            # Check for duplicate IDs
            if doc_id in self._documents:
                logger.warning(f"Document {doc_id} already exists, overwriting")
            
            # Store document and its components
            self._documents[doc_id] = document
            self._embeddings[doc_id] = document.embedding.copy()
            self._metadata[doc_id] = document.metadata
            
            logger.debug(f"Added document {doc_id} to in-memory store")
            return doc_id
            
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(
                f"Failed to add document: {str(e)}",
                store_type=self.store_name,
                operation="add_document",
                document_id=document.document_id,
                cause=e
            )
    
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
        try:
            if not documents:
                return []
            
            document_ids = []
            for document in documents:
                doc_id = await self.add_document(document)
                document_ids.append(doc_id)
            
            logger.debug(f"Added {len(document_ids)} documents to in-memory store")
            return document_ids
            
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(
                f"Failed to add documents batch: {str(e)}",
                store_type=self.store_name,
                operation="add_documents_batch",
                cause=e
            )
    
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
        try:
            return self._documents.get(document_id)
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to get document: {str(e)}",
                store_type=self.store_name,
                operation="get_document",
                document_id=document_id,
                cause=e
            )
    
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
        try:
            if document_id not in self._documents:
                return False
            
            # Validate embedding dimension
            if self._embedding_dimension is not None:
                if document.embedding.shape[0] != self._embedding_dimension:
                    raise VectorStoreError(
                        f"Embedding dimension mismatch: expected {self._embedding_dimension}, "
                        f"got {document.embedding.shape[0]}",
                        store_type=self.store_name,
                        operation="update_document",
                        document_id=document_id
                    )
            
            # Update document and its components
            document.document_id = document_id  # Ensure ID consistency
            self._documents[document_id] = document
            self._embeddings[document_id] = document.embedding.copy()
            self._metadata[document_id] = document.metadata
            
            logger.debug(f"Updated document {document_id} in in-memory store")
            return True
            
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(
                f"Failed to update document: {str(e)}",
                store_type=self.store_name,
                operation="update_document",
                document_id=document_id,
                cause=e
            )
    
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
        try:
            if document_id not in self._documents:
                return False
            
            # Remove document and its components
            del self._documents[document_id]
            del self._embeddings[document_id]
            del self._metadata[document_id]
            
            logger.debug(f"Deleted document {document_id} from in-memory store")
            return True
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to delete document: {str(e)}",
                store_type=self.store_name,
                operation="delete_document",
                document_id=document_id,
                cause=e
            )
    
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
        try:
            if not self._documents:
                return []
            
            # Validate query embedding dimension
            if self._embedding_dimension is not None:
                if query_embedding.shape[0] != self._embedding_dimension:
                    raise VectorStoreError(
                        f"Query embedding dimension mismatch: expected {self._embedding_dimension}, "
                        f"got {query_embedding.shape[0]}",
                        store_type=self.store_name,
                        operation="similarity_search"
                    )
            
            # Filter documents by metadata if specified
            candidate_ids = list(self._documents.keys())
            if metadata_filter:
                candidate_ids = self._filter_by_metadata(candidate_ids, metadata_filter)
            
            if not candidate_ids:
                return []
            
            # Prepare embeddings for batch similarity calculation
            candidate_embeddings = np.array([
                self._embeddings[doc_id] for doc_id in candidate_ids
            ])
            
            # Calculate similarities
            similarities = batch_cosine_similarity(query_embedding, candidate_embeddings)
            
            # Apply similarity threshold
            threshold = similarity_threshold or 0.0
            valid_indices = np.where(similarities >= threshold)[0]
            
            if len(valid_indices) == 0:
                return []
            
            # Get top-k results
            top_k_count = min(limit, len(valid_indices))
            top_indices = valid_indices[np.argsort(similarities[valid_indices])[::-1]][:top_k_count]
            
            # Build results
            results = []
            for idx in top_indices:
                doc_id = candidate_ids[idx]
                document = self._documents[doc_id]
                similarity_score = float(similarities[idx])
                results.append((document, similarity_score))
            
            logger.debug(f"Found {len(results)} similar documents")
            return results
            
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(
                f"Failed to perform similarity search: {str(e)}",
                store_type=self.store_name,
                operation="similarity_search",
                cause=e
            )
    
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
        try:
            if metadata_filter is None:
                return len(self._documents)
            
            candidate_ids = list(self._documents.keys())
            filtered_ids = self._filter_by_metadata(candidate_ids, metadata_filter)
            return len(filtered_ids)
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to count documents: {str(e)}",
                store_type=self.store_name,
                operation="count_documents",
                cause=e
            )
    
    async def clear_store(self) -> None:
        """
        Clear all documents from the store.
        
        Raises:
            VectorStoreError: If clear operation fails
        """
        try:
            self._documents.clear()
            self._embeddings.clear()
            self._metadata.clear()
            
            logger.info("Cleared all documents from in-memory store")
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to clear store: {str(e)}",
                store_type=self.store_name,
                operation="clear_store",
                cause=e
            )
    
    async def health_check(self) -> bool:
        """
        Check if the vector store is healthy and accessible.
        
        Returns:
            True if store is healthy, False otherwise
        """
        try:
            # Simple health check - try to count documents
            await self.count_documents()
            return True
            
        except Exception as e:
            logger.warning(f"In-memory vector store health check failed: {str(e)}")
            return False
    
    def _filter_by_metadata(
        self,
        document_ids: List[str],
        metadata_filter: Dict[str, Any]
    ) -> List[str]:
        """Filter document IDs by metadata criteria."""
        filtered_ids = []
        
        for doc_id in document_ids:
            metadata = self._metadata.get(doc_id)
            if metadata and self._matches_filter(metadata, metadata_filter):
                filtered_ids.append(doc_id)
        
        return filtered_ids
    
    def _matches_filter(self, metadata: VectorMetadata, filter_dict: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria."""
        for key, expected_value in filter_dict.items():
            if key == 'tags':
                # Check if any expected tags are present
                if isinstance(expected_value, list):
                    if not any(tag in metadata.tags for tag in expected_value):
                        return False
                else:
                    if expected_value not in metadata.tags:
                        return False
            elif key == 'categories':
                # Check if any expected categories are present
                if isinstance(expected_value, list):
                    if not any(cat in metadata.categories for cat in expected_value):
                        return False
                else:
                    if expected_value not in metadata.categories:
                        return False
            elif hasattr(metadata, key):
                actual_value = getattr(metadata, key)
                if actual_value != expected_value:
                    return False
            elif key in metadata.custom_fields:
                if metadata.custom_fields[key] != expected_value:
                    return False
            else:
                return False
        
        return True
    
    def _generate_document_id(self) -> str:
        """Generate a unique document ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"inmem_{timestamp}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        return {
            'store_type': self.store_name,
            'document_count': len(self._documents),
            'embedding_dimension': self._embedding_dimension,
            'is_persistent': self.is_persistent,
            'memory_usage_mb': self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        if not self._embeddings:
            return 0.0
        
        # Estimate based on embeddings (largest component)
        embedding_size = self._embedding_dimension or 0
        num_documents = len(self._embeddings)
        
        # Each float32 is 4 bytes
        embeddings_bytes = num_documents * embedding_size * 4
        
        # Add rough estimate for documents and metadata (text content)
        text_bytes = sum(len(doc.content.encode('utf-8')) for doc in self._documents.values())
        
        total_bytes = embeddings_bytes + text_bytes
        return total_bytes / (1024 * 1024)  # Convert to MB
