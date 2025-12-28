"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from llm_providers_library.models import LLMGenerationResult, EmbeddingResult
from llm_providers_library.model_config import LLMModelConfig


class LLMProvider(ABC):
    """
    Abstract base class for LLM provider implementations.
    
    This is a generic interface for interacting with different LLM providers.
    It does NOT contain business logic - only low-level provider interactions.
    """
    
    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = LLMModelConfig.DEFAULT_TEMPERATURE,
        max_tokens: int = LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS,
    ):
        """
        Initialize provider.
        
        Args:
            model: Model name/identifier
            api_key: API key for the provider
            temperature: Sampling temperature (default, can be overridden per call)
            max_tokens: Maximum tokens to generate (default, can be overridden per call)
        """
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider_name = self._get_provider_name()
    
    @abstractmethod
    def _get_provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic')."""
        pass
    
    @abstractmethod
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
        (like summary generation, question generation) should be implemented
        by clients using this generic method.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt/instruction
            temperature: Optional temperature override (uses instance default if None)
            max_tokens: Optional max_tokens override (uses instance default if None)
            **kwargs: Provider-specific parameters (e.g., use_grounding for Gemini)
            
        Returns:
            LLMGenerationResult with generated text
        """
        pass
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult with vector
            
        Raises:
            NotImplementedError: If the provider doesn't support embeddings
        """
        pass
