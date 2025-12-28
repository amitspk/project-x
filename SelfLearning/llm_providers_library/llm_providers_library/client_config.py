"""Configuration classes for LLM client."""

from typing import Optional
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """
    Configuration for LLM client.
    
    This class provides all the configuration needed to create and use an LLM client.
    API keys can be provided here or via environment variables (recommended).
    """
    
    api_key: Optional[str] = Field(None, description="API key for the LLM provider. If None, will use environment variables")
    model: str = Field(..., description="Model identifier (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet-20241022', 'gemini-1.5-pro')")
    temperature: float = Field(0.7, description="Sampling temperature (0.0 to 2.0)")
    max_tokens: int = Field(2000, description="Maximum tokens to generate")
    embedding_model: Optional[str] = Field(None, description="Embedding model (for OpenAI, defaults to 'text-embedding-3-small')")
    
    class Config:
        frozen = True

