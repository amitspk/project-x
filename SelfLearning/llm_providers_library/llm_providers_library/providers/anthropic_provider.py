"""Anthropic Claude LLM provider implementation."""

import logging
from typing import Optional
from anthropic import AsyncAnthropic
from llm_providers_library.models import LLMGenerationResult, EmbeddingResult
from llm_providers_library.providers.base import LLMProvider
from llm_providers_library.model_config import LLMModelConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation - generic LLM interactions only."""
    
    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = LLMModelConfig.DEFAULT_TEMPERATURE,
        max_tokens: int = LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS
    ):
        super().__init__(model, api_key, temperature, max_tokens)
        self.client = AsyncAnthropic(api_key=api_key)
        logger.info(f"✅ Anthropic Provider initialized (model: {self.model})")
    
    def _get_provider_name(self) -> str:
        return "anthropic"
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMGenerationResult:
        """
        Generate text using Anthropic Claude (generic method - no business logic).
        
        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
            
        Returns:
            LLMGenerationResult with generated text
        """
        # Use instance defaults if not provided
        final_temperature = temperature if temperature is not None else self.temperature
        final_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        try:
            # Anthropic uses system parameter instead of system message role
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=final_max_tokens,
                temperature=final_temperature,
                system=system_prompt if system_prompt else "You are a helpful assistant.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result_text = response.content[0].text
            # Anthropic provides input_tokens and output_tokens separately
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            logger.debug(f"✅ Anthropic text generated ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="anthropic"
            )
            
        except Exception as e:
            logger.error(f"❌ Anthropic text generation failed: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding.
        
        Note: Anthropic doesn't provide embeddings API.
        """
        logger.error("❌ Anthropic does not provide embeddings API")
        raise NotImplementedError(
            "Anthropic Claude does not provide an embeddings API. "
            "Please use OpenAI or Gemini for embeddings."
        )
