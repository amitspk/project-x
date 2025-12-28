"""
LLM Client - Main entry point for the LLM providers library.

This is the primary interface for using the library. Create an LLMClient instance
with an LLMConfig, then use it to generate text or embeddings.

This library provides generic LLM provider interactions - no business logic.
Clients should implement their own business logic on top of these generic methods.
"""

import logging
from typing import Optional

from llm_providers_library.client_config import LLMConfig
from llm_providers_library.models import LLMGenerationResult, EmbeddingResult
from llm_providers_library.providers.factory import LLMProviderFactory
from llm_providers_library.providers.base import LLMProvider
from llm_providers_library.model_config import LLMModelConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Main client for interacting with LLM providers.
    
    This client provides a unified interface to multiple LLM providers (OpenAI, Anthropic, Gemini).
    It automatically routes requests to the appropriate provider based on the model name.
    
    This is a generic client - it does NOT contain business logic like "generate_summary" or 
    "generate_questions". Clients should implement their own business logic using the 
    generic `generate_text()` and `generate_embedding()` methods.
    
    Example:
        ```python
        from llm_providers_library import LLMClient, LLMConfig
        
        config = LLMConfig(
            api_key="your-api-key",  # Optional, can use env vars
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2000
        )
        
        client = LLMClient(config)
        
        # Generic text generation
        result = await client.generate_text(
            prompt="What is Python?",
            system_prompt="You are a helpful assistant."
        )
        print(result.text)
        ```
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize LLM client with configuration.
        
        Args:
            config: LLMConfig instance with model, API key, and other settings
        """
        self.config = config
        self.model = config.model or LLMModelConfig.DEFAULT_MODEL
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.embedding_model = config.embedding_model
        
        # Create provider instance using factory
        self.provider: LLMProvider = LLMProviderFactory.create(
            model=self.model,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            embedding_model=config.embedding_model
        )
        
        logger.info(f"✅ LLM Client initialized (model: {self.model}, provider: {self.provider.provider_name})")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMGenerationResult:
        """
        Generate text from a prompt (generic method - no business logic).
        
        This is the core method for text generation. All business-specific logic
        should be implemented by clients using this generic method.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt/instruction
            temperature: Optional temperature override (uses config default if None)
            max_tokens: Optional max_tokens override (uses config default if None)
            **kwargs: Provider-specific parameters (e.g., use_grounding=True for Gemini)
            
        Returns:
            LLMGenerationResult with generated text
        """
        return await self.provider.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate an embedding vector for the provided text.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult with the embedding vector
            
        Raises:
            NotImplementedError: If the provider doesn't support embeddings (e.g., Anthropic)
        """
        return await self.provider.generate_embedding(text)
