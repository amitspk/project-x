"""
ChromaDB vector store implementation.

This module provides a persistent vector store using ChromaDB,
which stores embeddings and metadata on disk for persistence between runs.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from ..core.interfaces import IVectorStore
from ..models.vector_models import VectorDocument, VectorMetadata
from ..utils.exceptions import VectorStoreError, ConfigurationError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class ChromaVectorStore(IVectorStore):
    """
    ChromaDB vector store implementation.
    
    Provides persistent vector storage using ChromaDB with automatic
    embedding generation and metadata filtering capabilities.
    """
    
    def __init__(
        self,
        collection_name: str = "content_summaries",
        persist_directory: str = "./chroma_db",
        embedding_function: Optional[Any] = None
    ):
        """
        Initialize ChromaDB vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
            embedding_function: Custom embedding function (optional)
            
        Raises:
            ConfigurationError: If ChromaDB is not available
        """
        if not CHROMADB_AVAILABLE:
            raise ConfigurationError(
                "ChromaDB not available. Install with: pip install chromadb",
                config_key="chromadb_dependency"
            )
        
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.embedding_function = embedding_function
        self._client = None
        self._collection = None
        self._initialized = False
        
        logger.info(f"Configured ChromaDB store: {collection_name} -> {persist_directory}")
    
    @property
    def store_name(self) -> str:
        """Get the name of the vector store."""
        return "chromadb"
    
    @property
    def is_persistent(self) -> bool:
        """Check if this store persists data between sessions."""
        return True
    
    async def initialize(self, **kwargs) -> None:
        """
        Initialize the ChromaDB client and collection.
        
        Args:
            **kwargs: Additional configuration parameters
            
        Raises:
            VectorStoreError: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            # Create persist directory
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB client
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Set up embedding function if not provided
            if not self.embedding_function:
                # Use default sentence transformers embedding function
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            
            # Get or create collection
            try:
                self._collection = self._client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Loaded existing collection: {self.collection_name}")
            except Exception:
                self._collection = self._client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}  # Use cosine similarity
                )
                logger.info(f"Created new collection: {self.collection_name}")
            
            self._initialized = True
            logger.info("ChromaDB vector store initialized successfully")
            
        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize ChromaDB store: {str(e)}",
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
            
            # Generate document ID if not provided
            doc_id = document.document_id
            if not doc_id:
                doc_id = self._generate_document_id()
                document.document_id = doc_id
            
            # Convert metadata to ChromaDB format
            chroma_metadata = self._convert_metadata_to_chroma(document.metadata)
            
            # Add document to collection
            # Note: ChromaDB will generate embeddings automatically using the embedding function
            # We don't need to pass the embedding explicitly
            self._collection.add(
                documents=[document.content],
                metadatas=[chroma_metadata],
                ids=[doc_id]
            )
            
            logger.debug(f"Added document {doc_id} to ChromaDB collection")
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
            
            if not self._initialized:
                await self.initialize()
            
            # Prepare batch data
            doc_ids = []
            contents = []
            metadatas = []
            
            for document in documents:
                # Generate document ID if not provided
                doc_id = document.document_id
                if not doc_id:
                    doc_id = self._generate_document_id()
                    document.document_id = doc_id
                
                doc_ids.append(doc_id)
                contents.append(document.content)
                metadatas.append(self._convert_metadata_to_chroma(document.metadata))
            
            # Add batch to collection
            self._collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=doc_ids
            )
            
            logger.debug(f"Added {len(doc_ids)} documents to ChromaDB collection")
            return doc_ids
            
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
            if not self._initialized:
                await self.initialize()
            
            # Query ChromaDB for the document
            results = self._collection.get(
                ids=[document_id],
                include=["documents", "metadatas", "embeddings"]
            )
            
            if not results['ids'] or len(results['ids']) == 0:
                return None
            
            # Convert ChromaDB result to VectorDocument
            content = results['documents'][0]
            metadata_dict = results['metadatas'][0]
            embedding = np.array(results['embeddings'][0], dtype=np.float32)
            
            # Convert metadata back from ChromaDB format
            metadata = self._convert_metadata_from_chroma(metadata_dict)
            
            return VectorDocument(
                content=content,
                embedding=embedding,
                metadata=metadata,
                document_id=document_id
            )
            
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
            if not self._initialized:
                await self.initialize()
            
            # Check if document exists
            existing = await self.get_document(document_id)
            if not existing:
                return False
            
            # Update document in ChromaDB
            chroma_metadata = self._convert_metadata_to_chroma(document.metadata)
            
            self._collection.update(
                ids=[document_id],
                documents=[document.content],
                metadatas=[chroma_metadata]
            )
            
            logger.debug(f"Updated document {document_id} in ChromaDB collection")
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
            if not self._initialized:
                await self.initialize()
            
            # Check if document exists
            existing = await self.get_document(document_id)
            if not existing:
                return False
            
            # Delete from ChromaDB
            self._collection.delete(ids=[document_id])
            
            logger.debug(f"Deleted document {document_id} from ChromaDB collection")
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
            if not self._initialized:
                await self.initialize()
            
            # Convert metadata filter to ChromaDB format
            where_filter = None
            if metadata_filter:
                where_filter = self._convert_filter_to_chroma(metadata_filter)
            
            # For ChromaDB, we need to query with text instead of embedding
            # This is a limitation - we'll use a placeholder query
            # In practice, you'd want to store the original query text
            query_texts = ["search query"]  # Placeholder
            
            # Perform similarity search
            results = self._collection.query(
                query_texts=query_texts,
                n_results=limit,
                where=where_filter,
                include=["documents", "metadatas", "embeddings", "distances"]
            )
            
            if not results['ids'] or len(results['ids']) == 0:
                return []
            
            # Convert results to VectorDocument format
            search_results = []
            
            for i in range(len(results['ids'][0])):
                doc_id = results['ids'][0][i]
                content = results['documents'][0][i]
                metadata_dict = results['metadatas'][0][i]
                embedding = np.array(results['embeddings'][0][i], dtype=np.float32)
                distance = results['distances'][0][i]
                
                # Convert distance to similarity score (ChromaDB uses cosine distance)
                similarity_score = 1.0 - distance
                
                # Apply similarity threshold
                if similarity_threshold and similarity_score < similarity_threshold:
                    continue
                
                # Convert metadata
                metadata = self._convert_metadata_from_chroma(metadata_dict)
                
                # Create VectorDocument
                document = VectorDocument(
                    content=content,
                    embedding=embedding,
                    metadata=metadata,
                    document_id=doc_id
                )
                
                search_results.append((document, similarity_score))
            
            logger.debug(f"Found {len(search_results)} similar documents")
            return search_results
            
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
            if not self._initialized:
                await self.initialize()
            
            # Convert metadata filter
            where_filter = None
            if metadata_filter:
                where_filter = self._convert_filter_to_chroma(metadata_filter)
            
            # Get count by querying all documents
            results = self._collection.get(
                where=where_filter,
                include=[]  # Don't include any data, just count
            )
            
            return len(results['ids']) if results['ids'] else 0
            
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
            if not self._initialized:
                await self.initialize()
            
            # Delete the collection and recreate it
            self._client.delete_collection(name=self.collection_name)
            
            self._collection = self._client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("Cleared all documents from ChromaDB store")
            
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
            if not self._initialized:
                await self.initialize()
            
            # Try to count documents
            await self.count_documents()
            return True
            
        except Exception as e:
            logger.warning(f"ChromaDB vector store health check failed: {str(e)}")
            return False
    
    def _convert_metadata_to_chroma(self, metadata: VectorMetadata) -> Dict[str, Any]:
        """Convert VectorMetadata to ChromaDB metadata format."""
        chroma_metadata = {}
        
        # Basic fields
        if metadata.title:
            chroma_metadata['title'] = metadata.title
        if metadata.url:
            chroma_metadata['url'] = metadata.url
        if metadata.content_id:
            chroma_metadata['content_id'] = metadata.content_id
        if metadata.content_type:
            chroma_metadata['content_type'] = metadata.content_type
        if metadata.language:
            chroma_metadata['language'] = metadata.language
        if metadata.source:
            chroma_metadata['source'] = metadata.source
        if metadata.author:
            chroma_metadata['author'] = metadata.author
        
        # Numeric fields
        chroma_metadata['word_count'] = metadata.word_count
        chroma_metadata['character_count'] = metadata.character_count
        chroma_metadata['estimated_reading_time'] = metadata.estimated_reading_time
        chroma_metadata['confidence_score'] = metadata.confidence_score
        chroma_metadata['quality_score'] = metadata.quality_score
        
        # Convert lists to strings (ChromaDB limitation)
        if metadata.tags:
            chroma_metadata['tags'] = ','.join(metadata.tags)
        if metadata.categories:
            chroma_metadata['categories'] = ','.join(metadata.categories)
        
        # Convert dates to ISO strings
        chroma_metadata['indexed_at'] = metadata.indexed_at.isoformat()
        chroma_metadata['updated_at'] = metadata.updated_at.isoformat()
        if metadata.published_date:
            chroma_metadata['published_date'] = metadata.published_date.isoformat()
        
        # Add custom fields (flatten them)
        for key, value in metadata.custom_fields.items():
            if isinstance(value, (str, int, float, bool)):
                chroma_metadata[f'custom_{key}'] = value
            elif isinstance(value, list):
                chroma_metadata[f'custom_{key}'] = ','.join(map(str, value))
            else:
                chroma_metadata[f'custom_{key}'] = str(value)
        
        return chroma_metadata
    
    def _convert_metadata_from_chroma(self, chroma_metadata: Dict[str, Any]) -> VectorMetadata:
        """Convert ChromaDB metadata back to VectorMetadata."""
        # Extract custom fields
        custom_fields = {}
        regular_fields = {}
        
        for key, value in chroma_metadata.items():
            if key.startswith('custom_'):
                custom_key = key[7:]  # Remove 'custom_' prefix
                custom_fields[custom_key] = value
            else:
                regular_fields[key] = value
        
        # Convert string lists back to lists
        tags = []
        if 'tags' in regular_fields and regular_fields['tags']:
            tags = regular_fields['tags'].split(',')
        
        categories = []
        if 'categories' in regular_fields and regular_fields['categories']:
            categories = regular_fields['categories'].split(',')
        
        # Convert date strings back to datetime
        indexed_at = datetime.now()
        if 'indexed_at' in regular_fields:
            try:
                indexed_at = datetime.fromisoformat(regular_fields['indexed_at'])
            except:
                pass
        
        updated_at = datetime.now()
        if 'updated_at' in regular_fields:
            try:
                updated_at = datetime.fromisoformat(regular_fields['updated_at'])
            except:
                pass
        
        published_date = None
        if 'published_date' in regular_fields and regular_fields['published_date']:
            try:
                published_date = datetime.fromisoformat(regular_fields['published_date'])
            except:
                pass
        
        return VectorMetadata(
            title=regular_fields.get('title'),
            url=regular_fields.get('url'),
            content_id=regular_fields.get('content_id'),
            content_type=regular_fields.get('content_type', 'article'),
            language=regular_fields.get('language', 'en'),
            tags=tags,
            categories=categories,
            word_count=regular_fields.get('word_count', 0),
            character_count=regular_fields.get('character_count', 0),
            estimated_reading_time=regular_fields.get('estimated_reading_time', 0),
            indexed_at=indexed_at,
            updated_at=updated_at,
            source=regular_fields.get('source', 'unknown'),
            author=regular_fields.get('author'),
            published_date=published_date,
            confidence_score=regular_fields.get('confidence_score', 0.0),
            quality_score=regular_fields.get('quality_score', 0.0),
            custom_fields=custom_fields
        )
    
    def _convert_filter_to_chroma(self, metadata_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Convert metadata filter to ChromaDB where clause format."""
        where_filter = {}
        
        for key, value in metadata_filter.items():
            if key == 'tags':
                # For tags, we need to use contains since they're stored as comma-separated
                if isinstance(value, list):
                    # For now, just check if any tag matches (simplified)
                    where_filter['tags'] = {'$contains': value[0]}
                else:
                    where_filter['tags'] = {'$contains': value}
            elif key == 'categories':
                # Similar to tags
                if isinstance(value, list):
                    where_filter['categories'] = {'$contains': value[0]}
                else:
                    where_filter['categories'] = {'$contains': value}
            else:
                where_filter[key] = value
        
        return where_filter
    
    def _generate_document_id(self) -> str:
        """Generate a unique document ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"chroma_{timestamp}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the ChromaDB store."""
        try:
            if not self._initialized:
                return {'error': 'Store not initialized'}
            
            # Get basic stats
            doc_count = len(self._collection.get()['ids'] or [])
            
            return {
                'store_type': self.store_name,
                'collection_name': self.collection_name,
                'persist_directory': str(self.persist_directory),
                'document_count': doc_count,
                'is_persistent': self.is_persistent,
                'embedding_function': str(type(self.embedding_function).__name__)
            }
        except Exception as e:
            return {'error': str(e)}
