"""Service for Q&A operations using llm_providers_library."""

import logging
from typing import Optional

from llm_providers_library.client import LLMClient
from llm_providers_library.client_config import LLMConfig
from llm_providers_library.models import LLMGenerationResult
from llm_providers_library.model_config import LLMModelConfig
from fyi_widget_api.api.utils.prompts import QA_ANSWER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class QAService:
    """Service for answering questions using the llm_providers_library."""

    @staticmethod
    async def answer_question(
        question: str,
        context: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_grounding: bool = False,
        api_key: Optional[str] = None,
    ) -> LLMGenerationResult:
        """
        Answer a question using LLM.
        
        Args:
            question: The question to answer
            context: Optional context (currently unused but kept for API compatibility)
            model: Model name to use (defaults to LLMModelConfig.DEFAULT_MODEL)
            temperature: Temperature setting (defaults to LLMModelConfig.DEFAULT_TEMPERATURE)
            max_tokens: Max tokens setting (defaults to LLMModelConfig.DEFAULT_MAX_TOKENS_CHAT)
            use_grounding: If True, enables Google Search grounding (Gemini only)
            api_key: Optional API key (uses env vars if not provided)
            
        Returns:
            LLMGenerationResult with the answer
        """
        # Use defaults from model_config if not provided
        effective_model = model or LLMModelConfig.DEFAULT_MODEL
        effective_temperature = temperature if temperature is not None else LLMModelConfig.DEFAULT_TEMPERATURE
        effective_max_tokens = max_tokens if max_tokens is not None else LLMModelConfig.DEFAULT_MAX_TOKENS_CHAT
        
        logger.info(f"🤖 Answering question with model: {effective_model}, temp: {effective_temperature}, max_tokens: {effective_max_tokens}")
        
        # Create config
        config = LLMConfig(
            api_key=api_key,
            model=effective_model,
            temperature=effective_temperature,
            max_tokens=effective_max_tokens,
        )
        
        # Create client
        client = LLMClient(config)
        
        # Build user prompt (simple - just the question)
        user_prompt = question
        
        # Generate answer using generic library method
        result = await client.generate_text(
            prompt=user_prompt,
            system_prompt=QA_ANSWER_SYSTEM_PROMPT,
            temperature=effective_temperature,
            max_tokens=effective_max_tokens,
            use_grounding=use_grounding if client.provider.provider_name == "gemini" else False,
        )
        
        logger.info(f"✅ Question answered successfully (tokens: {result.tokens_used}, model: {result.model})")
        
        return result

