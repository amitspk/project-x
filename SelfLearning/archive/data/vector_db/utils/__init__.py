"""Utility modules for the vector database."""

from .exceptions import (
    VectorDBError,
    EmbeddingError,
    VectorStoreError,
    VectorSearchError,
    ConfigurationError
)

from .text_processing import (
    TextChunker,
    TextPreprocessor
)

from .similarity_metrics import (
    cosine_similarity,
    euclidean_distance,
    dot_product_similarity
)

__all__ = [
    # Exceptions
    "VectorDBError",
    "EmbeddingError", 
    "VectorStoreError",
    "VectorSearchError",
    "ConfigurationError",
    
    # Text processing
    "TextChunker",
    "TextPreprocessor",
    
    # Similarity metrics
    "cosine_similarity",
    "euclidean_distance", 
    "dot_product_similarity"
]
