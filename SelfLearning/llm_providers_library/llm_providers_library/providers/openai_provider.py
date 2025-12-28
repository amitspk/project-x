"""OpenAI LLM provider implementation."""

import logging
from typing import Optional
from openai import AsyncOpenAI
from llm_providers_library.models import LLMGenerationResult, EmbeddingResult
from llm_providers_library.providers.base import LLMProvider
from llm_providers_library.model_config import LLMModelConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation - generic LLM interactions only."""
    
    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = LLMModelConfig.DEFAULT_TEMPERATURE,
        max_tokens: int = LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS,
        embedding_model: Optional[str] = None
    ):
        super().__init__(model, api_key, temperature, max_tokens)
        self.client = AsyncOpenAI(api_key=api_key)
        self.embedding_model = embedding_model if embedding_model is not None else LLMModelConfig.DEFAULT_EMBEDDING_MODEL
        logger.info(f"✅ OpenAI Provider initialized (model: {self.model}, embedding: {self.embedding_model})")
    
    def _get_provider_name(self) -> str:
        return "openai"
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMGenerationResult:
        """
        Generate text using OpenAI (generic method - no business logic).
        
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
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=final_temperature,
                max_tokens=final_max_tokens
            )
            
            result_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.debug(f"✅ OpenAI text generated ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="openai"
            )
            
        except Exception as e:
            logger.error(f"❌ OpenAI text generation failed: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding using OpenAI."""
        logger.debug("🔢 Generating embedding with OpenAI...")
        
        try:
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars]
            
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"✅ Embedding generated ({len(embedding)} dimensions)")
            
            return EmbeddingResult(
                embedding=embedding,
                dimensions=len(embedding),
                model=self.embedding_model,
                provider="openai"
            )
            
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            raise
