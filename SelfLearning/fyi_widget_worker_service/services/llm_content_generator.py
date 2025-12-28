"""
LLM Content Generator - Multi-provider LLM abstraction layer with business logic.

This service contains business-specific logic for blog processing:
- Summary generation with specific prompts and JSON format
- Question-answer pair generation with specific prompts and JSON format
- Answer question endpoint with specific formatting

It uses the generic llm_providers_library for actual LLM interactions.
"""

import logging
from typing import Optional

# Import from the new library (generic LLM interactions)
from llm_providers_library import LLMClient, LLMConfig
from llm_providers_library.models import LLMGenerationResult, EmbeddingResult
from llm_providers_library.providers.base import LLMProvider
from llm_providers_library.model_config import LLMModelConfig

# Import business-specific prompts (not part of generic library)
from fyi_widget_worker_service.services.llm_prompts import (
    OUTPUT_FORMAT_INSTRUCTION,
    DEFAULT_QUESTIONS_PROMPT,
    DEFAULT_SUMMARY_PROMPT,
    QUESTIONS_JSON_FORMAT,
    SUMMARY_JSON_FORMAT,
    QA_ANSWER_SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)


class LLMContentGenerator:
    """
    LLM Content Generator - Business logic layer for blog processing.
    
    This class contains business-specific logic (prompt engineering, JSON formatting, etc.)
    and uses the generic llm_providers_library for actual LLM provider interactions.
    
    Business logic name: LLMContentGenerator (not LLMService).
    
    Three-Layer Prompt Architecture:
        1. System Prompt (Non-negotiable): Defines AI role + enforces JSON format
        2. User Instructions (Customizable): Content style/focus (custom or default)
        3. Format Template (Non-negotiable): Explicit JSON schema enforcement
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        temperature: float = LLMModelConfig.DEFAULT_TEMPERATURE,
        max_tokens: int = LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS,
        embedding_model: str = None
    ):
        """
        Initialize LLM Content Generator.
        
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
        
        # Create LLM client from the library (generic, no business logic)
        config = LLMConfig(
            api_key=api_key,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            embedding_model=embedding_model
        )
        self.client = LLMClient(config)
        self.provider: LLMProvider = self.client.provider
        
        logger.info(f"✅ LLM Content Generator initialized (model: {self.model}, provider: {self.provider.provider_name})")
    
    def _get_client_for_model(
        self, 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMClient:
        """
        Get LLM client for a specific model and parameters. 
        If model/params match instance, uses instance client.
        
        Args:
            model: Optional model name to override instance model
            temperature: Optional temperature to override instance temperature
            max_tokens: Optional max_tokens to override instance max_tokens
            
        Returns:
            LLMClient instance
        """
        # Use instance client if all parameters match
        use_instance = (
            (model is None or model == self.model) and
            (temperature is None or temperature == self.temperature) and
            (max_tokens is None or max_tokens == self.max_tokens)
        )
        
        if use_instance:
            return self.client
        
        # Create a new client with specified parameters
        final_model = model if model is not None else self.model
        final_temperature = temperature if temperature is not None else self.temperature
        final_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        logger.debug(
            f"🔄 Creating client: model={final_model}, "
            f"temp={final_temperature}, max_tokens={final_max_tokens}"
        )
        
        config = LLMConfig(
            api_key=None,  # Will use env vars
            model=final_model,
            temperature=final_temperature,
            max_tokens=final_max_tokens,
            embedding_model=self.embedding_model
        )
        return LLMClient(config)
    
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
        Generate a summary of blog content (business logic - uses generic library).
        
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
            
        Note: Grounding is NOT used for summary generation (only for question generation).
        This method does not accept use_grounding parameter to prevent accidental usage.
        
        Example custom_prompt:
            "You are a technical writer for developers.
            Create summaries that highlight implementation details,
            code patterns, and practical takeaways for engineers."
        """
        # Get client for this specific operation with custom parameters
        if model is None:
            logger.warning(f"⚠️  No model specified for summary generation, using instance model: {self.model}")
            model = self.model
        elif model != self.model:
            logger.info(f"📝 Using model {model} for summary generation (instance model: {self.model})")
        
        client = self._get_client_for_model(model, temperature, max_tokens)
        provider = client.provider
        
        # Log which provider is actually being used
        logger.info(f"📝 Summary generation will use provider: {provider.provider_name} with model: {provider.model}")
        if temperature is not None and temperature != self.temperature:
            logger.info(f"📝 Using temperature {temperature} for summary (instance: {self.temperature})")
        if max_tokens is not None and max_tokens != self.max_tokens:
            logger.info(f"📝 Using max_tokens {max_tokens} for summary (instance: {self.max_tokens})")
        
        if custom_prompt:
            logger.info(f"📝 Generating summary with CUSTOM prompt (length: {len(custom_prompt)} chars)")
            logger.info(f"   Custom prompt preview: {custom_prompt[:150]}...")
        else:
            logger.info("📝 Generating summary with DEFAULT prompt (fallback)")
        
        # Build business-specific prompt (this is business logic)
        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_SUMMARY_PROMPT
        
        user_prompt = f"""{role_and_instructions}

Title: {title}

Content:
{content[:4000]}

REQUIRED OUTPUT FORMAT (you must use this exact JSON structure):
{SUMMARY_JSON_FORMAT}"""
        
        # Log the complete prompts being sent to LLM
        logger.debug("=" * 80)
        logger.debug("FINAL PROMPT SENT TO LLM (generate_summary):")
        logger.debug("=" * 80)
        logger.debug(f"System Message:\n{OUTPUT_FORMAT_INSTRUCTION}")
        logger.debug("-" * 80)
        
        # Use generic library method with business-specific prompts
        return await client.generate_text(
            prompt=user_prompt,
            system_prompt=OUTPUT_FORMAT_INSTRUCTION,
            temperature=temperature if temperature is not None else 0.5,  # Lower for more factual summaries
            max_tokens=max_tokens if max_tokens is not None else 500  # Shorter for summaries
        )
    
    async def generate_questions(
        self, 
        content: str, 
        title: str = "",
        num_questions: int = 5,
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_grounding: bool = False
    ) -> LLMGenerationResult:
        """
        Generate question-answer pairs from content (business logic - uses generic library).
        
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
            use_grounding: If True, enables Google Search grounding (Gemini only) for real-time information.
                          Note: Grounding is ONLY available for question generation, NOT for summary or embeddings.
            
        Returns:
            LLMGenerationResult with questions in JSON format
        
        Example custom_prompt:
            "You are a senior software engineer creating technical Q&A.
            Generate questions that focus on implementation details,
            code examples, and best practices. Use technical terminology
            appropriate for experienced developers."
        """
        # Get client for this specific operation with custom parameters
        client = self._get_client_for_model(model, temperature, max_tokens)
        provider = client.provider
        
        if model and model != self.model:
            logger.info(f"❓ Using model {model} for questions generation (instance model: {self.model})")
        if temperature is not None and temperature != self.temperature:
            logger.info(f"❓ Using temperature {temperature} for questions (instance: {self.temperature})")
        if max_tokens is not None and max_tokens != self.max_tokens:
            logger.info(f"❓ Using max_tokens {max_tokens} for questions (instance: {self.max_tokens})")
        
        if custom_prompt:
            logger.info(f"❓ Generating {num_questions} questions with CUSTOM prompt (length: {len(custom_prompt)} chars)")
            logger.info(f"   Custom prompt preview: {custom_prompt[:150]}...")
        else:
            logger.info(f"❓ Generating {num_questions} questions with DEFAULT prompt (fallback)")
        
        # Build business-specific prompt (this is business logic)
        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_QUESTIONS_PROMPT
        
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
        
        # Use generic library method with business-specific prompts
        # Pass use_grounding as kwargs for Gemini provider-specific feature
        return await client.generate_text(
            prompt=user_prompt,
            system_prompt=OUTPUT_FORMAT_INSTRUCTION,
            temperature=temperature,
            max_tokens=max_tokens,
            use_grounding=use_grounding if provider.provider_name == "gemini" else False
        )
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text (delegates directly to library).
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult with vector
        """
        # Direct delegation - no business logic needed
        return await self.client.generate_embedding(text)
    
    async def answer_question(
        self, 
        question: str, 
        context: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_grounding: bool = False
    ) -> LLMGenerationResult:
        """
        Answer a user's question with optional context (business logic - uses generic library).
        
        This method implements business-specific formatting requirements for Q&A responses.
        
        Args:
            question: User's question
            context: Optional context to help answer the question
            model: Optional model name to override instance model for this operation
            temperature: Optional temperature to override instance temperature for this operation
            max_tokens: Optional max_tokens to override instance max_tokens for this operation
            use_grounding: If True, enables Google Search grounding (Gemini only) for real-time information
            
        Returns:
            LLMGenerationResult with answer
        """
        # Get client for this specific operation with custom parameters
        client = self._get_client_for_model(model, temperature, max_tokens)
        provider = client.provider
        
        if model and model != self.model:
            logger.info(f"💬 Using model {model} for chat/question answering (instance model: {self.model})")
        if temperature is not None and temperature != self.temperature:
            logger.info(f"💬 Using temperature {temperature} for chat (instance: {self.temperature})")
        if max_tokens is not None and max_tokens != self.max_tokens:
            logger.info(f"💬 Using max_tokens {max_tokens} for chat (instance: {self.max_tokens})")
        
        # Build business-specific prompt (this is business logic)
        if context:
            user_prompt = f"""Context:
{context[:2000]}

Question: {question}

Provide a clear, concise answer based on the context above."""
        else:
            user_prompt = f"Question: {question}\n\nProvide a helpful, accurate answer."
        
        # Use system prompt from prompts file
        system_prompt = QA_ANSWER_SYSTEM_PROMPT
        
        # Cap max_tokens at 350 to enforce 150-200 word limit
        effective_max_tokens = min(350, max_tokens if max_tokens is not None else self.max_tokens)
        
        # Use generic library method with business-specific prompts
        # Pass use_grounding as kwargs for Gemini provider-specific feature
        return await client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            use_grounding=use_grounding if provider.provider_name == "gemini" else False
        )
