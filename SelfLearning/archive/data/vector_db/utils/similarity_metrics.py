"""
Similarity metrics for vector operations.

This module provides various similarity and distance metrics
for comparing embeddings and ranking search results.
"""

import numpy as np
from typing import List, Tuple, Union
from scipy.spatial.distance import cosine as scipy_cosine
from scipy.spatial.distance import euclidean as scipy_euclidean


def cosine_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Cosine similarity measures the cosine of the angle between two vectors,
    providing a value between -1 and 1, where 1 indicates identical direction.
    
    Args:
        vector1: First vector
        vector2: Second vector
        
    Returns:
        Cosine similarity score between -1 and 1
        
    Raises:
        ValueError: If vectors have different dimensions or are empty
    """
    if vector1.size == 0 or vector2.size == 0:
        raise ValueError("Vectors cannot be empty")
    
    if vector1.shape != vector2.shape:
        raise ValueError(f"Vector dimensions must match: {vector1.shape} vs {vector2.shape}")
    
    # Handle zero vectors
    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    # Calculate cosine similarity
    dot_product = np.dot(vector1, vector2)
    similarity = dot_product / (norm1 * norm2)
    
    # Ensure result is within valid range due to floating point precision
    return max(-1.0, min(1.0, similarity))


def cosine_distance(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Calculate cosine distance between two vectors.
    
    Cosine distance is 1 - cosine_similarity, providing a distance metric
    where 0 indicates identical vectors and 2 indicates opposite vectors.
    
    Args:
        vector1: First vector
        vector2: Second vector
        
    Returns:
        Cosine distance between 0 and 2
    """
    return 1.0 - cosine_similarity(vector1, vector2)


def euclidean_distance(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Calculate Euclidean distance between two vectors.
    
    Euclidean distance is the straight-line distance between two points
    in n-dimensional space.
    
    Args:
        vector1: First vector
        vector2: Second vector
        
    Returns:
        Euclidean distance (always non-negative)
        
    Raises:
        ValueError: If vectors have different dimensions or are empty
    """
    if vector1.size == 0 or vector2.size == 0:
        raise ValueError("Vectors cannot be empty")
    
    if vector1.shape != vector2.shape:
        raise ValueError(f"Vector dimensions must match: {vector1.shape} vs {vector2.shape}")
    
    return float(np.linalg.norm(vector1 - vector2))


def manhattan_distance(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Calculate Manhattan (L1) distance between two vectors.
    
    Manhattan distance is the sum of absolute differences between
    corresponding elements of the vectors.
    
    Args:
        vector1: First vector
        vector2: Second vector
        
    Returns:
        Manhattan distance (always non-negative)
        
    Raises:
        ValueError: If vectors have different dimensions or are empty
    """
    if vector1.size == 0 or vector2.size == 0:
        raise ValueError("Vectors cannot be empty")
    
    if vector1.shape != vector2.shape:
        raise ValueError(f"Vector dimensions must match: {vector1.shape} vs {vector2.shape}")
    
    return float(np.sum(np.abs(vector1 - vector2)))


def dot_product_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Calculate dot product similarity between two vectors.
    
    The dot product provides a similarity measure that considers both
    the magnitude and direction of vectors.
    
    Args:
        vector1: First vector
        vector2: Second vector
        
    Returns:
        Dot product similarity
        
    Raises:
        ValueError: If vectors have different dimensions or are empty
    """
    if vector1.size == 0 or vector2.size == 0:
        raise ValueError("Vectors cannot be empty")
    
    if vector1.shape != vector2.shape:
        raise ValueError(f"Vector dimensions must match: {vector1.shape} vs {vector2.shape}")
    
    return float(np.dot(vector1, vector2))


def normalized_dot_product_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
    """
    Calculate normalized dot product similarity between two vectors.
    
    This is equivalent to cosine similarity but computed differently.
    Vectors are normalized before computing the dot product.
    
    Args:
        vector1: First vector
        vector2: Second vector
        
    Returns:
        Normalized dot product similarity between -1 and 1
    """
    # Normalize vectors
    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    normalized_v1 = vector1 / norm1
    normalized_v2 = vector2 / norm2
    
    return dot_product_similarity(normalized_v1, normalized_v2)


def batch_cosine_similarity(
    query_vector: np.ndarray,
    document_vectors: np.ndarray
) -> np.ndarray:
    """
    Calculate cosine similarity between a query vector and multiple document vectors.
    
    This is optimized for batch operations and is more efficient than
    computing similarities one by one.
    
    Args:
        query_vector: Query vector of shape (embedding_dim,)
        document_vectors: Document vectors of shape (num_docs, embedding_dim)
        
    Returns:
        Array of cosine similarities of shape (num_docs,)
        
    Raises:
        ValueError: If dimensions don't match or vectors are empty
    """
    if query_vector.size == 0 or document_vectors.size == 0:
        raise ValueError("Vectors cannot be empty")
    
    if len(document_vectors.shape) != 2:
        raise ValueError("Document vectors must be 2D array")
    
    if query_vector.shape[0] != document_vectors.shape[1]:
        raise ValueError(
            f"Vector dimensions must match: {query_vector.shape[0]} vs {document_vectors.shape[1]}"
        )
    
    # Normalize query vector
    query_norm = np.linalg.norm(query_vector)
    if query_norm == 0:
        return np.zeros(document_vectors.shape[0])
    
    normalized_query = query_vector / query_norm
    
    # Normalize document vectors
    doc_norms = np.linalg.norm(document_vectors, axis=1)
    
    # Handle zero vectors
    zero_mask = doc_norms == 0
    doc_norms[zero_mask] = 1  # Avoid division by zero
    
    normalized_docs = document_vectors / doc_norms.reshape(-1, 1)
    
    # Calculate similarities
    similarities = np.dot(normalized_docs, normalized_query)
    
    # Set similarities to 0 for zero vectors
    similarities[zero_mask] = 0.0
    
    return similarities


def top_k_similar(
    query_vector: np.ndarray,
    document_vectors: np.ndarray,
    k: int,
    similarity_threshold: float = 0.0
) -> List[Tuple[int, float]]:
    """
    Find top-k most similar documents to a query vector.
    
    Args:
        query_vector: Query vector
        document_vectors: Array of document vectors
        k: Number of top results to return
        similarity_threshold: Minimum similarity threshold
        
    Returns:
        List of (index, similarity_score) tuples sorted by similarity (descending)
        
    Raises:
        ValueError: If k is invalid or vectors are empty
    """
    if k <= 0:
        raise ValueError("k must be positive")
    
    if document_vectors.shape[0] == 0:
        return []
    
    # Calculate similarities
    similarities = batch_cosine_similarity(query_vector, document_vectors)
    
    # Filter by threshold
    valid_indices = np.where(similarities >= similarity_threshold)[0]
    
    if len(valid_indices) == 0:
        return []
    
    # Get top-k indices
    valid_similarities = similarities[valid_indices]
    top_k_count = min(k, len(valid_indices))
    
    # Get indices of top-k similarities (in descending order)
    top_k_local_indices = np.argpartition(valid_similarities, -top_k_count)[-top_k_count:]
    top_k_local_indices = top_k_local_indices[np.argsort(valid_similarities[top_k_local_indices])[::-1]]
    
    # Convert back to original indices
    top_k_indices = valid_indices[top_k_local_indices]
    top_k_similarities = similarities[top_k_indices]
    
    return list(zip(top_k_indices.tolist(), top_k_similarities.tolist()))


def similarity_matrix(vectors: np.ndarray) -> np.ndarray:
    """
    Calculate pairwise cosine similarity matrix for a set of vectors.
    
    Args:
        vectors: Array of vectors of shape (num_vectors, embedding_dim)
        
    Returns:
        Similarity matrix of shape (num_vectors, num_vectors)
        
    Raises:
        ValueError: If vectors array is invalid
    """
    if vectors.size == 0:
        raise ValueError("Vectors array cannot be empty")
    
    if len(vectors.shape) != 2:
        raise ValueError("Vectors must be 2D array")
    
    num_vectors = vectors.shape[0]
    similarity_mat = np.zeros((num_vectors, num_vectors))
    
    # Normalize all vectors
    norms = np.linalg.norm(vectors, axis=1)
    zero_mask = norms == 0
    norms[zero_mask] = 1  # Avoid division by zero
    
    normalized_vectors = vectors / norms.reshape(-1, 1)
    
    # Calculate similarity matrix using matrix multiplication
    similarity_mat = np.dot(normalized_vectors, normalized_vectors.T)
    
    # Set similarities to 0 for zero vectors
    similarity_mat[zero_mask, :] = 0.0
    similarity_mat[:, zero_mask] = 0.0
    
    # Ensure diagonal is 1.0 for non-zero vectors
    for i in range(num_vectors):
        if not zero_mask[i]:
            similarity_mat[i, i] = 1.0
    
    return similarity_mat


def diversity_score(vectors: np.ndarray) -> float:
    """
    Calculate diversity score for a set of vectors.
    
    Diversity score is the average pairwise distance between vectors,
    indicating how diverse or similar the vector set is.
    
    Args:
        vectors: Array of vectors of shape (num_vectors, embedding_dim)
        
    Returns:
        Diversity score (higher values indicate more diversity)
        
    Raises:
        ValueError: If vectors array is invalid
    """
    if vectors.size == 0:
        raise ValueError("Vectors array cannot be empty")
    
    if vectors.shape[0] < 2:
        return 0.0  # No diversity with less than 2 vectors
    
    # Calculate similarity matrix
    sim_matrix = similarity_matrix(vectors)
    
    # Convert similarities to distances
    distance_matrix = 1.0 - sim_matrix
    
    # Calculate average pairwise distance (excluding diagonal)
    num_vectors = vectors.shape[0]
    total_distance = 0.0
    pair_count = 0
    
    for i in range(num_vectors):
        for j in range(i + 1, num_vectors):
            total_distance += distance_matrix[i, j]
            pair_count += 1
    
    return total_distance / pair_count if pair_count > 0 else 0.0
