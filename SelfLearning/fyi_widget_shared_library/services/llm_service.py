"""
LLM Service - Multi-provider LLM abstraction layer.

Handles all LLM operations: summarization, question generation, embeddings.
Uses factory pattern to route to appropriate provider (OpenAI, Anthropic, etc.).

Three-Layer Prompt Architecture:
    1. System Prompt (Non-negotiable): Defines AI role + enforces JSON format
    2. User Instructions (Customizable): Content style/focus (custom or default)
    3. Format Template (Non-negotiable): Explicit JSON schema enforcement
"""

import logging
import json
from typing import List, Dict, Any, Tuple, Optional

# Configuration handled by service-specific configs
from fyi_widget_shared_library.models.schemas import LLMGenerationResult, EmbeddingResult
from .llm_providers.factory import LLMProviderFactory
from .llm_providers.base import LLMProvider
from .llm_providers.model_config import LLMModelConfig
# Import shared prompts and format templates (moved to separate module to avoid circular imports)
from .llm_prompts import (
    OUTPUT_FORMAT_INSTRUCTION,
    DEFAULT_QUESTIONS_PROMPT,
    DEFAULT_SUMMARY_PROMPT,
    QUESTIONS_JSON_FORMAT,
    SUMMARY_JSON_FORMAT
)

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM Service - Facade for multi-provider LLM operations.
    
    Automatically routes to the correct provider (OpenAI, Anthropic, etc.)
    based on the model name. Uses factory pattern for provider creation.
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,  # Increased for detailed Q&A generation
        embedding_model: str = None
    ):
        """
        Initialize LLM Service.
        
        Args:
            api_key: Optional API key (if not provided, fetched from env vars based on provider)
            model: Model identifier (determines provider automatically). If None, uses DEFAULT_MODEL from LLMModelConfig
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            embedding_model: Embedding model (only used for OpenAI). If None, uses DEFAULT_EMBEDDING_MODEL from LLMModelConfig
        """
        # Use default model from config if not specified
        self.model = model if model is not None else LLMModelConfig.DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.embedding_model = embedding_model if embedding_model is not None else LLMModelConfig.DEFAULT_EMBEDDING_MODEL
        
        # Create provider instance using factory
        # Use self.model (which has default applied) instead of raw model parameter
        self.provider: LLMProvider = LLMProviderFactory.create(
            model=self.model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            embedding_model=embedding_model  # Factory will apply default if None
        )
        
        logger.info(f"✅ LLM Service initialized (model: {self.model}, provider: {self.provider.provider_name})")
    
    def _get_provider_for_model(
        self, 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMProvider:
        """
        Get provider for a specific model and parameters. 
        If model/params match instance, uses instance provider.
        
        Args:
            model: Optional model name to override instance model
            temperature: Optional temperature to override instance temperature
            max_tokens: Optional max_tokens to override instance max_tokens
            
        Returns:
            LLMProvider instance
        """
        # Use instance provider if all parameters match
        use_instance = (
            (model is None or model == self.model) and
            (temperature is None or temperature == self.temperature) and
            (max_tokens is None or max_tokens == self.max_tokens)
        )
        
        if use_instance:
            return self.provider
        
        # Create a new provider with specified parameters
        final_model = model if model is not None else self.model
        final_temperature = temperature if temperature is not None else self.temperature
        final_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        logger.debug(
            f"🔄 Creating provider: model={final_model}, "
            f"temp={final_temperature}, max_tokens={final_max_tokens}"
        )
        return LLMProviderFactory.create(
            model=final_model,
            api_key=None,  # Factory will fetch from env vars
            temperature=final_temperature,
            max_tokens=final_max_tokens,
            embedding_model=self.embedding_model
        )
    
    async def generate_summary(
        self, 
        content: str, 
        title: str = "",
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMGenerationResult:
        """
        Generate a summary of blog content.
        
        Two-part prompt architecture:
        - Part 1 (System): Pure output format enforcement
        - Part 2 (User): Role + Instructions (custom or default fallback)
        
        Args:
            content: Blog content
            title: Blog title (optional)
            custom_prompt: Optional custom prompt including role and instructions
                          If None, uses DEFAULT_SUMMARY_PROMPT (fallback)
            model: Optional model name to override instance model for this operation
            temperature: Optional temperature to override instance temperature for this operation
            max_tokens: Optional max_tokens to override instance max_tokens for this operation
            
        Returns:
            LLMGenerationResult with summary in JSON format
        
        Example custom_prompt:
            "You are a technical writer for developers.
            Create summaries that highlight implementation details,
            code patterns, and practical takeaways for engineers."
        """
        # Get provider for this specific operation with custom parameters
        provider = self._get_provider_for_model(model, temperature, max_tokens)
        if model and model != self.model:
            logger.info(f"📝 Using model {model} for summary generation (instance model: {self.model})")
        if temperature is not None and temperature != self.temperature:
            logger.info(f"📝 Using temperature {temperature} for summary (instance: {self.temperature})")
        if max_tokens is not None and max_tokens != self.max_tokens:
            logger.info(f"📝 Using max_tokens {max_tokens} for summary (instance: {self.max_tokens})")
        
        if custom_prompt:
            logger.info(f"📝 Generating summary with CUSTOM prompt (length: {len(custom_prompt)} chars)")
            logger.info(f"   Custom prompt preview: {custom_prompt[:150]}...")
        else:
            logger.info("📝 Generating summary with DEFAULT prompt (fallback)")
        
        # Log the complete prompts being sent to LLM
        logger.debug("=" * 80)
        logger.debug("FINAL PROMPT SENT TO LLM (generate_summary):")
        logger.debug("=" * 80)
        logger.debug(f"System Message:\n{OUTPUT_FORMAT_INSTRUCTION}")
        logger.debug("-" * 80)
        
        # Delegate to provider
        return await provider.generate_summary(
            content=content,
            title=title,
            custom_prompt=custom_prompt,
            system_prompt=OUTPUT_FORMAT_INSTRUCTION
        )
    
    async def generate_questions(
        self, 
        content: str, 
        title: str = "",
        num_questions: int = 5,
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMGenerationResult:
        """
        Generate question-answer pairs from content.
        
        Two-part prompt architecture:
        - Part 1 (System): Pure output format enforcement
        - Part 2 (User): Role + Instructions (custom or default fallback)
        
        Args:
            content: Blog content
            title: Blog title
            num_questions: Number of Q&A pairs to generate
            custom_prompt: Optional custom prompt including role and instructions
                          If None, uses DEFAULT_QUESTIONS_PROMPT (fallback)
            model: Optional model name to override instance model for this operation
            temperature: Optional temperature to override instance temperature for this operation
            max_tokens: Optional max_tokens to override instance max_tokens for this operation
            
        Returns:
            LLMGenerationResult with questions in JSON format
        
        Example custom_prompt:
            "You are a senior software engineer creating technical Q&A.
            Generate questions that focus on implementation details,
            code examples, and best practices. Use technical terminology
            appropriate for experienced developers."
        """
        # Get provider for this specific operation with custom parameters
        provider = self._get_provider_for_model(model, temperature, max_tokens)
        if model and model != self.model:
            logger.info(f"❓ Using model {model} for questions generation (instance model: {self.model})")
        if temperature is not None and temperature != self.temperature:
            logger.info(f"❓ Using temperature {temperature} for questions (instance: {self.temperature})")
        if max_tokens is not None and max_tokens != self.max_tokens:
            logger.info(f"❓ Using max_tokens {max_tokens} for questions (instance: {self.max_tokens})")
        
        # Part 2: Use custom prompt or fallback to default
        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_QUESTIONS_PROMPT
        
        if custom_prompt:
            logger.info(f"❓ Generating {num_questions} questions with CUSTOM prompt (length: {len(custom_prompt)} chars)")
            logger.info(f"   Custom prompt preview: {custom_prompt[:150]}...")
        else:
            logger.info(f"❓ Generating {num_questions} questions with DEFAULT prompt (fallback)")
        
        # Build user prompt: Role+Instructions + Content + Format Template
        user_prompt = f"""{role_and_instructions}

Title: {title}

Content:
{content[:4000]}

Generate exactly {num_questions} question-answer pairs.

REQUIRED OUTPUT FORMAT (you must use this exact JSON structure):
{QUESTIONS_JSON_FORMAT}"""

        # Log the complete prompts being sent to LLM
        logger.debug("=" * 80)
        logger.debug("FINAL PROMPT SENT TO LLM (generate_questions):")
        logger.debug("=" * 80)
        logger.debug(f"System Message:\n{OUTPUT_FORMAT_INSTRUCTION}")
        logger.debug("-" * 80)
        
        # Delegate to provider
        return await provider.generate_questions(
            content=content,
            title=title,
            num_questions=num_questions,
            custom_prompt=custom_prompt,
            system_prompt=OUTPUT_FORMAT_INSTRUCTION
        )
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult with vector
        """
        # Delegate to provider
        return await self.provider.generate_embedding(text)
    
    async def answer_question(
        self, 
        question: str, 
        context: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMGenerationResult:
        """
        Answer a user's question with optional context.
        
        Args:
            question: User's question
            context: Optional context to help answer the question
            model: Optional model name to override instance model for this operation
            temperature: Optional temperature to override instance temperature for this operation
            max_tokens: Optional max_tokens to override instance max_tokens for this operation
            
        Returns:
            LLMGenerationResult with answer
        """
        # Get provider for this specific operation with custom parameters
        provider = self._get_provider_for_model(model, temperature, max_tokens)
        if model and model != self.model:
            logger.info(f"💬 Using model {model} for chat/question answering (instance model: {self.model})")
        if temperature is not None and temperature != self.temperature:
            logger.info(f"💬 Using temperature {temperature} for chat (instance: {self.temperature})")
        if max_tokens is not None and max_tokens != self.max_tokens:
            logger.info(f"💬 Using max_tokens {max_tokens} for chat (instance: {self.max_tokens})")
        
        return await provider.answer_question(question=question, context=context)

