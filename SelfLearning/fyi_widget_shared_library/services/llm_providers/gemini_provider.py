"""Google Gemini LLM provider implementation."""

import asyncio
import logging
from typing import Optional

try:
    import google.generativeai as genai
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise ImportError(
        "google-generativeai package is required for Gemini support. "
        "Install it by adding 'google-generativeai' to your requirements."
    ) from exc

from fyi_widget_shared_library.models.schemas import EmbeddingResult, LLMGenerationResult
from .base import LLMProvider
from .model_config import LLMModelConfig

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini provider implementation."""

    DEFAULT_EMBEDDING_MODEL = "text-embedding-004"

    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = LLMModelConfig.DEFAULT_TEMPERATURE,
        max_tokens: int = LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS,
        embedding_model: Optional[str] = None,
    ):
        super().__init__(model, api_key, temperature, max_tokens)
        genai.configure(api_key=api_key)
        self._base_generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        self.embedding_model = embedding_model or self.DEFAULT_EMBEDDING_MODEL
        # Store a default client without system instructions; we'll build others per call if needed
        self._model_client = genai.GenerativeModel(model_name=self.model)
        logger.info(
            "✅ Gemini Provider initialized (model: %s, embedding: %s)",
            self.model,
            self.embedding_model,
        )

    def _get_provider_name(self) -> str:
        return "gemini"

    async def generate_summary(
        self,
        content: str,
        title: str = "",
        custom_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMGenerationResult:
        from ..llm_prompts import DEFAULT_SUMMARY_PROMPT, SUMMARY_JSON_FORMAT

        role_and_instructions = custom_prompt if custom_prompt else DEFAULT_SUMMARY_PROMPT
        system_msg = system_prompt or ""

        user_prompt = f"""{role_and_instructions}

Title: {title}

Content:
{content[:4000]}

REQUIRED OUTPUT FORMAT (you must use this exact JSON structure):
{SUMMARY_JSON_FORMAT}"""

        logger.debug(
            "📝 Gemini generating summary (system: %d chars, user: %d chars)",
            len(system_msg),
            len(user_prompt),
        )

        text, tokens_used = await self._generate_content(
            prompt=user_prompt,
            system_instruction=system_msg or "You are a helpful assistant that returns JSON.",
            temperature=0.5,
            max_output_tokens=min(700, self.max_tokens),
        )

        return LLMGenerationResult(
            text=text,
            tokens_used=tokens_used,
            model=self.model,
            provider=self.provider_name,
        )

    async def generate_questions(
        self,
        content: str,
        title: str = "",
        num_questions: int = 5,
        custom_prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMGenerationResult:
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

        logger.debug(
            "❓ Gemini generating %d questions (system: %d chars, user: %d chars)",
            num_questions,
            len(system_msg),
            len(user_prompt),
        )

        text, tokens_used = await self._generate_content(
            prompt=user_prompt,
            system_instruction=system_msg or "You are a helpful assistant that returns JSON.",
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )

        return LLMGenerationResult(
            text=text,
            tokens_used=tokens_used,
            model=self.model,
            provider=self.provider_name,
        )

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        logger.info("🔢 Generating embedding with Gemini (model: %s)...", self.embedding_model)

        truncated_text = text[:8000]
        try:
            response = await asyncio.to_thread(
                genai.embed_content,
                model=self.embedding_model,
                content=truncated_text,
            )
        except Exception as exc:
            logger.error("❌ Embedding generation failed: %s", exc)
            raise

        embedding = response["embedding"]
        logger.info("✅ Embedding generated (%d dimensions)", len(embedding))

        return EmbeddingResult(
            embedding=embedding,
            dimensions=len(embedding),
            model=self.embedding_model,
        )

    async def answer_question(
        self,
        question: str,
        context: str = "",
    ) -> LLMGenerationResult:
        logger.info("💬 Answering question with Gemini: %s...", question[:50])

        if context:
            prompt = f"""Context:
{context[:2000]}

Question: {question}

Provide a clear, concise answer based on the context above."""
        else:
            prompt = f"Question: {question}\n\nProvide a helpful, accurate answer."

        text, tokens_used = await self._generate_content(
            prompt=prompt,
            system_instruction="You are a helpful assistant.",
            temperature=self.temperature,
            max_output_tokens=min(600, self.max_tokens),
        )

        return LLMGenerationResult(
            text=text,
            tokens_used=tokens_used,
            model=self.model,
            provider=self.provider_name,
        )

    async def _generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str],
        temperature: Optional[float],
        max_output_tokens: Optional[int],
    ) -> tuple[str, int]:
        generation_config = self._base_generation_config.copy()
        if temperature is not None:
            generation_config["temperature"] = temperature
        if max_output_tokens is not None:
            generation_config["max_output_tokens"] = max_output_tokens

        if system_instruction:
            model_client = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_instruction,
            )
        else:
            model_client = self._model_client

        try:
            response = await asyncio.to_thread(
                model_client.generate_content,
                [{"role": "user", "parts": [prompt]}],
                generation_config=generation_config,
            )
        except Exception as exc:
            logger.error("❌ Gemini content generation failed: %s", exc)
            raise

        result_text = getattr(response, "text", None)
        if not result_text:
            logger.error("❌ Gemini returned empty response for prompt preview: %s", prompt[:120])
            raise ValueError("Gemini returned an empty response.")

        tokens_used = 0
        usage = getattr(response, "usage_metadata", None)
        if usage:
            tokens_used = (
                getattr(usage, "total_token_count", None)
                or (
                    (getattr(usage, "prompt_token_count", 0) or 0)
                    + (getattr(usage, "candidates_token_count", 0) or 0)
                )
            )

        logger.info(
            "✅ Gemini generation succeeded (%s tokens)",
            tokens_used if tokens_used else "unknown",
        )

        return result_text, int(tokens_used) if tokens_used else 0


