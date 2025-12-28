"""
Internal schema models for Worker service.

These models are used for internal service communication and data processing.
"""

from typing import List, Dict, Any
from pydantic import BaseModel


# ============================================================================
# Internal Service Models
# ============================================================================

class CrawledContent(BaseModel):
    """Crawled content from web."""
    url: str
    title: str
    content: str
    language: str
    word_count: int
    metadata: Dict[str, Any] = {}


class LLMGenerationResult(BaseModel):
    """Result from LLM generation."""
    text: str
    tokens_used: int
    model: str
    provider: str


class EmbeddingResult(BaseModel):
    """Result from embedding generation."""
    embedding: List[float]
    dimensions: int
    model: str

