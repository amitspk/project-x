"""Anthropic Claude LLM provider implementation."""

import logging
from typing import Optional
from anthropic import AsyncAnthropic
from fyi_widget_shared_library.models.schemas import LLMGenerationResult, EmbeddingResult
from .base import LLMProvider
from .model_config import LLMModelConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
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
    
    async def generate_summary(
        self,
        content: str,
        title: str = "",
        custom_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMGenerationResult:
        """Generate summary using Anthropic Claude."""
        from ..llm_prompts import DEFAULT_SUMMARY_PROMPT, SUMMARY_JSON_FORMAT
        
        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_SUMMARY_PROMPT
        system_msg = system_prompt or ""
        
        user_prompt = f"""{role_and_instructions}

Title: {title}

Content:
{content[:4000]}

REQUIRED OUTPUT FORMAT (you must use this exact JSON structure):
{SUMMARY_JSON_FORMAT}"""

        logger.debug(f"📝 Anthropic generating summary (system: {len(system_msg)} chars, user: {len(user_prompt)} chars)")

        try:
            # Anthropic uses system parameter instead of system message role
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.5,  # Lower for more factual summaries
                system=system_msg if system_msg else "You are a helpful assistant.",
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            result_text = response.content[0].text
            # Anthropic provides input_tokens and output_tokens separately
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            logger.info(f"✅ Summary generated ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="anthropic"
            )
            
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            raise
    
    async def generate_questions(
        self,
        content: str,
        title: str = "",
        num_questions: int = 5,
        custom_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMGenerationResult:
        """Generate questions using Anthropic Claude."""
        from ..llm_prompts import DEFAULT_QUESTIONS_PROMPT, QUESTIONS_JSON_FORMAT
        
        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_QUESTIONS_PROMPT
        system_msg = system_prompt or ""
        
        user_prompt = f"""{role_and_instructions}

Title: {title}

Content:
{content[:4000]}

Generate exactly {num_questions} question-answer pairs.

REQUIRED OUTPUT FORMAT (you must use this exact JSON structure):
{QUESTIONS_JSON_FORMAT}"""

        logger.debug(f"❓ Anthropic generating {num_questions} questions (system: {len(system_msg)} chars, user: {len(user_prompt)} chars)")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_msg if system_msg else "You are a helpful assistant.",
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            result_text = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            logger.info(f"✅ Questions generated ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="anthropic"
            )
            
        except Exception as e:
            logger.error(f"❌ Question generation failed: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding.
        
        Note: Anthropic doesn't provide embeddings API.
        Falls back to OpenAI embeddings or raises error.
        """
        logger.error("❌ Anthropic does not provide embeddings API")
        raise NotImplementedError(
            "Anthropic Claude does not provide an embeddings API. "
            "Please use OpenAI for embeddings or configure a hybrid setup."
        )
    
    async def answer_question(
        self,
        question: str,
        context: str = ""
    ) -> LLMGenerationResult:
        """Answer question using Anthropic Claude."""
        logger.info(f"💬 Answering question with Anthropic: {question[:50]}...")
        
        if context:
            prompt = f"""Context:
{context[:2000]}

Question: {question}

Provide a clear, concise answer based on the context above."""
        else:
            prompt = f"Question: {question}\n\nProvide a helpful, accurate answer."
        
        # System prompt for Q&A endpoint (strict formatting and length limits)
        system_prompt = """Role: You are an expert AI assistant. Your goal is to answer a user's specific question clearly, accurately, and authoritatively.

Core Principles:

1. Go Beyond the Surface: Do not just give a simple one-word or one-sentence answer. Briefly explain the "how" or "why" to provide genuine knowledge expansion.

2. Be Clear and Direct: Write in simple, easy-to-understand language. Use active voice and eliminate all clutter (e.g., use "use," not "utilize").

Strict Formatting Rules (for Readability & Cost):

* Be Concise: Keep the entire answer to a maximum of 150-200 words (1000 characters). This is a strict limit.

* Format for Scanning: Use short paragraphs (with <br><br>).

* Bolding: Emphasize 3-5 of the most critical concepts using <b>...</b> tags.

* The Payoff: End every answer with a single summary line: <b>Key Takeaway:</b> [The one-sentence summary of the answer].

* No Chit-Chat: Do not use conversational filler like "Hello!", "That's a great question!", or "Here is the answer:". Respond only with the formatted answer itself."""

        try:
            # Cap max_tokens at 350 to enforce 150-200 word limit from system prompt
            # but still respect publisher's configured chat_max_tokens if lower
            effective_max_tokens = min(350, self.max_tokens)
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=effective_max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result_text = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            logger.info(f"✅ Question answered ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="anthropic"
            )
            
        except Exception as e:
            logger.error(f"❌ Question answering failed: {e}")
            raise

