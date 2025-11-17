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
        
        # Initialize new SDK client for grounding support (required for Google Search grounding)
        self._new_sdk_client = None
        try:
            from google import genai as new_genai
            from google.genai.types import HttpOptions
            self._new_sdk_client = new_genai.Client(api_key=api_key, http_options=HttpOptions(api_version="v1beta"))
            logger.debug("✅ New SDK (google-genai) client initialized with v1beta for grounding support")
        except (ImportError, AttributeError):
            logger.debug("⚠️ New SDK (google-genai) not available - grounding will be unavailable")
            self._new_sdk_client = None
        
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
        """
        Generate summary from content.
        
        Note: Grounding is NOT used for summary generation (only for question generation).
        This method does not accept use_grounding parameter to prevent accidental usage.
        """
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

        # Note: use_grounding is NOT passed here - grounding is only for question generation
        text, tokens_used = await self._generate_content(
            prompt=user_prompt,
            system_instruction=system_msg or "You are a helpful assistant that returns JSON.",
            temperature=0.5,
            max_output_tokens=min(700, self.max_tokens),
            use_grounding=False,  # Explicitly disabled - grounding only for question generation
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
        use_grounding: bool = False,
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
            "❓ Gemini generating %d questions (system: %d chars, user: %d chars, grounding: %s)",
            num_questions,
            len(system_msg),
            len(user_prompt),
            use_grounding,
        )
        
        # Log full prompt for question generation
        prompt_type = "CUSTOM" if custom_prompt else "DEFAULT_QUESTIONS_PROMPT"
        logger.info("📝 Full question generation prompt before LLM call:")
        logger.info(f"   Prompt Type: {prompt_type}")
        logger.info(f"   System Instruction ({len(system_msg) if system_msg else 0} chars):\n{system_msg if system_msg else '(empty - using default fallback)'}")
        logger.info(f"   User Prompt ({len(user_prompt)} chars):\n{user_prompt}")
        logger.info(f"   Configuration: model={self.model}, temperature={self.temperature}, max_tokens={self.max_tokens}, grounding={use_grounding}")

        text, tokens_used = await self._generate_content(
            prompt=user_prompt,
            system_instruction=system_msg or "You are a helpful assistant that returns JSON.",
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            use_grounding=use_grounding,
        )

        return LLMGenerationResult(
            text=text,
            tokens_used=tokens_used,
            model=self.model,
            provider=self.provider_name,
        )

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding from text.
        
        Note: Grounding is NOT used for embedding generation (only for question generation).
        Embeddings use a separate API that doesn't support grounding.
        """
        logger.info("🔢 Generating embedding with Gemini (model: %s)...", self.embedding_model)

        truncated_text = text[:8000]
        try:
            # Note: Embeddings use a separate API that doesn't support grounding
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
        use_grounding: bool = False,
    ) -> LLMGenerationResult:
        """
        Answer a user question.
        
        Note: Grounding is disabled for Q&A endpoint (cost control).
        Grounding should only be used for question generation during blog processing.
        This method accepts use_grounding parameter for backward compatibility but
        it should always be set to False when called from the Q&A API endpoint.
        """
        logger.info("💬 Answering question with Gemini: %s... (grounding: %s)", question[:50], use_grounding)

        if context:
            prompt = f"""Context:
{context[:2000]}

Question: {question}

Provide a clear, concise answer based on the context above."""
        else:
            prompt = f"Question: {question}\n\nProvide a helpful, accurate answer."

        # System prompt for Q&A endpoint (strict formatting and length limits)
        system_instruction = """Role: You are an expert AI assistant. Your goal is to answer a user's specific question clearly, accurately, and authoritatively.

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

        # Note: use_grounding should be False for Q&A endpoint (cost control)
        # Grounding is only used for question generation during blog processing
        # Max tokens set to ~350 to enforce 150-200 word limit (approximately 1 token per 4 characters)
        text, tokens_used = await self._generate_content(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=self.temperature,
            max_output_tokens=min(350, self.max_tokens),
            use_grounding=use_grounding,
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
        use_grounding: bool = False,
    ) -> tuple[str, int]:
        """
        Generate content using Gemini API.
        
        Args:
            prompt: User prompt
            system_instruction: System instruction/role
            temperature: Sampling temperature
            max_output_tokens: Maximum output tokens
            use_grounding: If True, enables Google Search grounding for real-time information
            
        Returns:
            Tuple of (generated_text, tokens_used)
        """
        # If grounding is enabled, use new SDK API
        if use_grounding:
            if not self._new_sdk_client:
                raise ImportError(
                    "Google Search grounding requires the 'google-genai' SDK. "
                    "Install it with: pip install google-genai"
                )
            
            from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
            
            # Build config with tools for grounding
            config_dict = {
                "temperature": temperature or self.temperature,
                "max_output_tokens": max_output_tokens or self.max_tokens,
                "tools": [Tool(google_search=GoogleSearch())]
            }
            if system_instruction:
                config_dict["system_instruction"] = system_instruction
            
            config = GenerateContentConfig(**config_dict)
            
            logger.debug("🔍 Using Google Search grounding for Gemini generation")
            
            # Use new SDK client API
            response = await asyncio.to_thread(
                self._new_sdk_client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config,
            )
            
            # Check for safety blocks or other finish reasons
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, "finish_reason", None)
                
                # Helper function to check if finish_reason is STOP (normal completion)
                def is_stop_reason(fr):
                    """Check if finish_reason represents STOP (normal completion)."""
                    if fr is None:
                        return True  # No finish_reason means success (default)
                    
                    # Check enum name
                    if hasattr(fr, 'name') and fr.name == "STOP":
                        return True
                    
                    # Check enum value
                    if hasattr(fr, 'value') and fr.value == 1:
                        return True
                    
                    # Check if it's an int with value 1
                    if isinstance(fr, int) and fr == 1:
                        return True
                    
                    # Check string representation (handles cases like "FinishReason.STOP")
                    fr_str = str(fr).upper()
                    if "STOP" in fr_str and ("FINISH_REASON" in fr_str or "1" in fr_str or fr_str.count(".") > 0):
                        return True
                    
                    return False
                
                # Log finish_reason for debugging
                if finish_reason is not None:
                    logger.debug(f"🔍 Finish reason: {finish_reason} (type: {type(finish_reason).__name__})")
                    if is_stop_reason(finish_reason):
                        logger.debug("✅ Finish reason is STOP - normal completion, proceeding with response")
                    else:
                        logger.warning(f"⚠️  Finish reason is NOT STOP: {finish_reason}")
                
                # Only treat non-STOP finish reasons as errors
                if finish_reason is not None and not is_stop_reason(finish_reason):
                    # Extract numeric value if available for mapping
                    finish_reason_value = None
                    if hasattr(finish_reason, 'value'):
                        finish_reason_value = finish_reason.value
                    elif isinstance(finish_reason, int):
                        finish_reason_value = finish_reason
                    
                    finish_reason_map = {
                        2: "SAFETY (blocked by safety filters)",
                        3: "RECITATION (content matched blocked content)",
                        4: "OTHER (unknown reason)",
                    }
                    reason_text = finish_reason_map.get(finish_reason_value, f"FINISH_REASON_{finish_reason}")
                    
                    # Extract detailed safety ratings
                    safety_details = []
                    safety_ratings = getattr(candidate, "safety_ratings", [])
                    if safety_ratings:
                        for rating in safety_ratings:
                            category = getattr(rating, "category", None)
                            probability = getattr(rating, "probability", None)
                            blocked = getattr(rating, "blocked", False)
                            
                            if blocked or probability:
                                # Format category name (remove HARM_CATEGORY_ prefix if present)
                                cat_str = str(category).replace("HARM_CATEGORY_", "").replace("_", " ").title() if category else "UNKNOWN"
                                prob_str = str(probability).replace("HARM_PROBABILITY_", "").replace("_", " ").title() if probability else "UNKNOWN"
                                
                                safety_details.append(
                                    f"{cat_str} (Probability: {prob_str}, Blocked: {blocked})"
                                )
                    
                    # Build detailed error message
                    error_msg = f"Gemini content generation was blocked ({reason_text})"
                    if safety_details:
                        error_msg += f". Safety details: {'; '.join(safety_details)}"
                    else:
                        error_msg += ". No detailed safety ratings available"
                    
                    # Log full details including prompt preview
                    logger.error("❌ Gemini response blocked: %s (prompt preview: %s)", reason_text, prompt[:200])
                    if safety_details:
                        logger.error("   Safety details: %s", "; ".join(safety_details))
                    
                    raise ValueError(error_msg)
            
            # Extract response text (only if not blocked)
            try:
                result_text = getattr(response, "text", None) or str(response)
            except Exception as exc:
                logger.error("❌ Failed to extract text from Gemini response: %s", exc)
                raise ValueError(
                    "Gemini response did not contain valid content. "
                    "This may be due to safety filtering or content policy restrictions."
                ) from exc
            
            # Extract token usage (new SDK returns usage_metadata as an object)
            tokens_used = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage_metadata = response.usage_metadata
                tokens_used = (
                    getattr(usage_metadata, "total_token_count", None) or
                    getattr(usage_metadata, "prompt_token_count", 0) +
                    getattr(usage_metadata, "candidates_token_count", 0)
                )
            
            logger.info(
                "✅ Gemini generation succeeded with grounding (%s tokens)",
                tokens_used if tokens_used else "unknown",
            )
            
            return result_text, int(tokens_used) if tokens_used else 0
        
        # Use old SDK (original implementation)
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
            # Build the call arguments
            # First positional argument: contents
            contents = [{"role": "user", "parts": [prompt]}]
            
            # Keyword arguments
            call_kwargs = {
                "generation_config": generation_config,
            }
            
            response = await asyncio.to_thread(
                model_client.generate_content,
                contents,
                **call_kwargs,
            )
        except Exception as exc:
            logger.error("❌ Gemini content generation failed: %s", exc)
            raise

        # Check for safety blocks or other finish reasons before accessing text
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)
            
            # Helper function to check if finish_reason is STOP (normal completion)
            def is_stop_reason(fr):
                """Check if finish_reason represents STOP (normal completion)."""
                if fr is None:
                    return True  # No finish_reason means success (default)
                
                # Check enum name
                if hasattr(fr, 'name') and fr.name == "STOP":
                    return True
                
                # Check enum value
                if hasattr(fr, 'value') and fr.value == 1:
                    return True
                
                # Check if it's an int with value 1
                if isinstance(fr, int) and fr == 1:
                    return True
                
                # Check string representation (handles cases like "FinishReason.STOP")
                fr_str = str(fr).upper()
                if "STOP" in fr_str and ("FINISH_REASON" in fr_str or "1" in fr_str or fr_str.count(".") > 0):
                    return True
                
                return False
            
            # Log finish_reason for debugging
            if finish_reason is not None:
                logger.debug(f"🔍 Finish reason: {finish_reason} (type: {type(finish_reason).__name__})")
                if is_stop_reason(finish_reason):
                    logger.debug("✅ Finish reason is STOP - normal completion, proceeding with response")
                else:
                    logger.warning(f"⚠️  Finish reason is NOT STOP: {finish_reason}")
            
            # Only treat non-STOP finish reasons as errors
            if finish_reason is not None and not is_stop_reason(finish_reason):
                # Extract numeric value if available for mapping
                finish_reason_value = None
                if hasattr(finish_reason, 'value'):
                    finish_reason_value = finish_reason.value
                elif isinstance(finish_reason, int):
                    finish_reason_value = finish_reason
                
                finish_reason_map = {
                    2: "SAFETY (blocked by safety filters)",
                    3: "RECITATION (content matched blocked content)",
                    4: "OTHER (unknown reason)",
                }
                reason_text = finish_reason_map.get(finish_reason_value, f"FINISH_REASON_{finish_reason}")
                
                # Extract detailed safety ratings
                safety_details = []
                safety_ratings = getattr(candidate, "safety_ratings", [])
                if safety_ratings:
                    for rating in safety_ratings:
                        category = getattr(rating, "category", None)
                        probability = getattr(rating, "probability", None)
                        blocked = getattr(rating, "blocked", False)
                        
                        # Include all ratings, not just blocked ones, to give full context
                        if probability or blocked:
                            # Format category name (remove HARM_CATEGORY_ prefix if present)
                            cat_str = str(category).replace("HARM_CATEGORY_", "").replace("_", " ").title() if category else "UNKNOWN"
                            prob_str = str(probability).replace("HARM_PROBABILITY_", "").replace("_", " ").title() if probability else "UNKNOWN"
                            
                            if blocked:
                                safety_details.append(
                                    f"{cat_str} (Probability: {prob_str}, BLOCKED)"
                                )
                            else:
                                # Also log non-blocked ratings for context
                                safety_details.append(
                                    f"{cat_str} (Probability: {prob_str}, allowed)"
                                )
                
                # Build detailed error message
                error_msg = f"Gemini content generation was blocked ({reason_text})"
                if safety_details:
                    error_msg += f". Safety details: {'; '.join(safety_details)}"
                else:
                    error_msg += ". No detailed safety ratings available"
                
                # Log full details including prompt preview
                logger.error("❌ Gemini response blocked: %s (prompt preview: %s)", reason_text, prompt[:200])
                if safety_details:
                    logger.error("   Safety details: %s", "; ".join(safety_details))
                    # Log blocked categories separately for emphasis
                    blocked_only = [d for d in safety_details if "BLOCKED" in d]
                    if blocked_only:
                        logger.error("   BLOCKED categories: %s", "; ".join(blocked_only))
                
                raise ValueError(error_msg)

        # Extract response text (only if not blocked)
        try:
            result_text = getattr(response, "text", None)
        except Exception as exc:
            logger.error("❌ Failed to extract text from Gemini response: %s (prompt preview: %s)", exc, prompt[:120])
            raise ValueError(
                "Gemini response did not contain valid content. "
                "This may be due to safety filtering or content policy restrictions."
            ) from exc
        
        if not result_text:
            logger.error("❌ Gemini returned empty response for prompt preview: %s", prompt[:120])
            raise ValueError(
                "Gemini returned an empty response. "
                "This may be due to safety filters or content policy restrictions."
            )

        # Extract token usage
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
