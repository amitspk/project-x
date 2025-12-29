"""Configuration classes for LLM client."""

from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class LLMLibraryConfig(BaseSettings):
    """
    Library-level configuration for API keys.
    
    Reads API keys from environment variables using Pydantic BaseSettings.
    The .env file is read from the current working directory of the application
    using the library (e.g., worker service's .env when used in worker).
    
    This allows the library to be self-contained and not depend on external config,
    while still respecting the host application's environment configuration.
    """
    
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")  # Alternative name for Gemini
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    
    class Config:
        env_file = ".env"  # Reads from current working directory of the host application
        case_sensitive = False
        extra = "ignore"


# Global config instance (loaded once when module is imported)
# Uses the .env file from the current working directory at import time
_library_config = LLMLibraryConfig()


def get_library_config() -> LLMLibraryConfig:
    """Get the library configuration instance."""
    return _library_config


class LLMConfig(BaseModel):
    """
    Configuration for LLM client.
    
    This class provides all the configuration needed to create and use an LLM client.
    API keys are automatically read from environment variables by the library using BaseSettings.
    """
    
    model: str = Field(..., description="Model identifier (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet-20241022', 'gemini-1.5-pro')")
    temperature: float = Field(0.7, description="Sampling temperature (0.0 to 2.0)")
    max_tokens: int = Field(2000, description="Maximum tokens to generate")
    embedding_model: Optional[str] = Field(None, description="Embedding model (for OpenAI, defaults to 'text-embedding-3-large' with 3072 dimensions)")
    
    class Config:
        frozen = True

