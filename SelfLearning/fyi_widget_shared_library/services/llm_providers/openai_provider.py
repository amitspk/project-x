"""OpenAI LLM provider implementation."""

import logging
from typing import Optional
from openai import AsyncOpenAI
from fyi_widget_shared_library.models.schemas import LLMGenerationResult, EmbeddingResult
from .base import LLMProvider
from .model_config import LLMModelConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
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
    
    async def generate_summary(
        self,
        content: str,
        title: str = "",
        custom_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMGenerationResult:
        """Generate summary using OpenAI."""
        # Import shared prompts
        from ..llm_prompts import DEFAULT_SUMMARY_PROMPT, SUMMARY_JSON_FORMAT
        
        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_SUMMARY_PROMPT
        system_msg = system_prompt or ""
        
        user_prompt = f"""{role_and_instructions}

Title: {title}

Content:
{content[:4000]}

REQUIRED OUTPUT FORMAT (you must use this exact JSON structure):
{SUMMARY_JSON_FORMAT}"""

        logger.debug(f"📝 OpenAI generating summary (system: {len(system_msg)} chars, user: {len(user_prompt)} chars)")

        try:
            messages = []
            if system_msg:
                messages.append({"role": "system", "content": system_msg})
            messages.append({"role": "user", "content": user_prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,  # Lower for more factual summaries
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"✅ Summary generated ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="openai"
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
        """Generate questions using OpenAI."""
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

        logger.debug(f"❓ OpenAI generating {num_questions} questions (system: {len(system_msg)} chars, user: {len(user_prompt)} chars)")

        try:
            messages = []
            if system_msg:
                messages.append({"role": "system", "content": system_msg})
            messages.append({"role": "user", "content": user_prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            result_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"✅ Questions generated ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="openai"
            )
            
        except Exception as e:
            logger.error(f"❌ Question generation failed: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding using OpenAI."""
        logger.info("🔢 Generating embedding with OpenAI...")
        
        try:
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars]
            
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            embedding = response.data[0].embedding
            
            logger.info(f"✅ Embedding generated ({len(embedding)} dimensions)")
            
            return EmbeddingResult(
                embedding=embedding,
                dimensions=len(embedding),
                model=self.embedding_model
            )
            
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            raise
    
    async def answer_question(
        self,
        question: str,
        context: str = ""
    ) -> LLMGenerationResult:
        """Answer question using OpenAI."""
        logger.info(f"💬 Answering question with OpenAI: {question[:50]}...")
        
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

MANDATORY FORMATTING REQUIREMENTS (YOU MUST FOLLOW THESE EXACTLY):

1. Paragraph Structure (REQUIRED): You MUST break your answer into multiple short paragraphs. Each paragraph should be 2-3 sentences maximum. Separate paragraphs with <br><br> (two line breaks). NEVER write everything in one continuous paragraph. 

2. Bolding (REQUIRED): You MUST use HTML <b>...</b> tags to bold 3-5 of the most critical concepts, key terms, or important phrases in your answer. Do NOT use Markdown syntax (** or __) - ONLY use HTML <b> tags. For example: <b>important concept</b> NOT **important concept**. Do NOT skip bolding - it is mandatory.

3. Key Takeaway (REQUIRED): End every answer with exactly this format on its own line: <b>Key Takeaway:</b> [The one-sentence summary]

4. Length Limit: Keep the entire answer to a maximum of 150-200 words (1000 characters). This is a strict limit.

5. No Chit-Chat: Do not use conversational filler like "Hello!", "That's a great question!", or "Here is the answer:". Start directly with the formatted answer.

CRITICAL: Use ONLY HTML tags (<b>, <br><br>) - NEVER use Markdown (** or __ or #).

EXAMPLE OF CORRECT FORMAT (note the HTML tags, NOT Markdown):

<b>Solar eclipses</b> occur when the Moon passes between Earth and the Sun, casting a shadow on Earth's surface. This alignment happens approximately every 18 months somewhere on Earth.<br><br>

The <b>path of totality</b>, where the Moon completely blocks the Sun, is typically 100-150 miles wide. Observers outside this path see a partial eclipse, where only part of the Sun is covered.<br><br>

<b>Total solar eclipses</b> last only 2-7 minutes at any given location, making them rare and spectacular events. The next total solar eclipse visible from the United States will occur on April 8, 2024.<br><br>

<b>Key Takeaway:</b> Solar eclipses happen when the Moon blocks the Sun's light, with total eclipses visible only along a narrow path on Earth."""

        try:
            # Cap max_tokens at 350 to enforce 150-200 word limit from system prompt
            # but still respect publisher's configured chat_max_tokens if lower
            effective_max_tokens = min(350, self.max_tokens)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=effective_max_tokens
            )
            
            result_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"✅ Question answered ({tokens_used} tokens)")
            
            return LLMGenerationResult(
                text=result_text,
                tokens_used=tokens_used,
                model=self.model,
                provider="openai"
            )
            
        except Exception as e:
            logger.error(f"❌ Question answering failed: {e}")
            raise

