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

from llm_providers_library.models import EmbeddingResult, LLMGenerationResult
from llm_providers_library.providers.base import LLMProvider
from llm_providers_library.model_config import LLMModelConfig

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini provider implementation - generic LLM interactions only."""

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

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_grounding: bool = False,
        **kwargs
    ) -> LLMGenerationResult:
        """
        Generate text using Gemini (generic method - no business logic).
        
        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt/instruction
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
            use_grounding: If True, enables Google Search grounding for real-time information (Gemini-specific)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMGenerationResult with generated text
        """
        # Use instance defaults if not provided
        final_temperature = temperature if temperature is not None else self.temperature
        final_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        text, tokens_used = await self._generate_content(
            prompt=prompt,
            system_instruction=system_prompt or "You are a helpful assistant.",
            temperature=final_temperature,
            max_output_tokens=final_max_tokens,
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
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingResult with vector
        """
        logger.debug("🔢 Generating embedding with Gemini (model: %s)...", self.embedding_model)

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
        logger.debug("✅ Embedding generated (%d dimensions)", len(embedding))

        return EmbeddingResult(
            embedding=embedding,
            dimensions=len(embedding),
            model=self.embedding_model,
            provider="gemini"
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
        Generate content using Gemini API (internal helper method).
        
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
            
            logger.debug(
                "✅ Gemini generation succeeded with grounding (%s tokens)",
                tokens_used if tokens_used else "unknown",
            )
            
            return result_text, int(tokens_used) if tokens_used else 0
        
        # Use old SDK (original implementation, no grounding)
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
            contents = [{"role": "user", "parts": [prompt]}]
            
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

        logger.debug(
            "✅ Gemini generation succeeded (%s tokens)",
            tokens_used if tokens_used else "unknown",
        )

        return result_text, int(tokens_used) if tokens_used else 0
