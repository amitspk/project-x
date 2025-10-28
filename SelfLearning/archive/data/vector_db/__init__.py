"""
Vector Database Module for Content Embeddings and Similarity Search.

This module provides enterprise-grade vector database capabilities for:
- Converting content to embeddings using multiple providers
- Storing vectors with metadata in various vector databases
- Performing similarity searches with advanced filtering
- Integration with existing content processing pipeline

Key Components:
- Core interfaces and abstractions
- Multiple embedding providers (OpenAI, Anthropic, local models)
- Vector storage backends (Chroma, FAISS, Pinecone)
- Similarity search with metadata filtering
- Production-ready error handling and monitoring
"""

from .core.interfaces import (
    IEmbeddingProvider,
    IVectorStore,
    IVectorSearchService
)

from .models.vector_models import (
    VectorDocument,
    EmbeddingRequest,
    SearchRequest,
    SearchResult,
    VectorMetadata
)

from .services.vector_service import VectorSearchService
from .services.embedding_service import EmbeddingService

__version__ = "1.0.0"
__author__ = "SelfLearning Project"

__all__ = [
    # Core interfaces
    "IEmbeddingProvider",
    "IVectorStore", 
    "IVectorSearchService",
    
    # Models
    "VectorDocument",
    "EmbeddingRequest",
    "SearchRequest", 
    "SearchResult",
    "VectorMetadata",
    
    # Services
    "VectorSearchService",
    "EmbeddingService"
]
