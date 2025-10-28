"""Core interfaces and abstractions for the vector database module."""

from .interfaces import (
    IEmbeddingProvider,
    IVectorStore,
    IVectorSearchService
)

__all__ = [
    "IEmbeddingProvider",
    "IVectorStore", 
    "IVectorSearchService"
]
