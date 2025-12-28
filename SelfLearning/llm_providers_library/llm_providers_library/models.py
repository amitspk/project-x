"""Result models for LLM operations."""

from typing import List, Optional
from pydantic import BaseModel, Field


class LLMGenerationResult(BaseModel):
    """Result from LLM generation operations (summary, questions, answers)."""
    
    text: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model used for generation")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    provider: str = Field(..., description="Provider name (openai, anthropic, gemini)")
    
    class Config:
        frozen = True


class EmbeddingResult(BaseModel):
    """Result from embedding generation."""
    
    embedding: List[float] = Field(..., description="Embedding vector")
    dimensions: Optional[int] = Field(None, description="Number of dimensions in the embedding")
    model: str = Field(..., description="Model used for embedding")
    provider: Optional[str] = Field(None, description="Provider name (openai, anthropic, gemini)")
    
    class Config:
        frozen = True

