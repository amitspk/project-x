"""
LLM Providers Library

A standalone, reusable library for interacting with multiple LLM providers
(OpenAI, Anthropic, Gemini).

Main exports:
    - LLMClient: Main client class for LLM operations
    - LLMConfig: Configuration class for the client
    - LLMGenerationResult: Result model for generation operations
    - EmbeddingResult: Result model for embedding operations
"""

from llm_providers_library.client import LLMClient
from llm_providers_library.client_config import LLMConfig
from llm_providers_library.models import LLMGenerationResult, EmbeddingResult

__all__ = [
    "LLMClient",
    "LLMConfig",
    "LLMGenerationResult",
    "EmbeddingResult",
]

__version__ = "0.1.0"

