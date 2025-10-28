"""
Q&A service for the blog manager microservice.

Handles general question-answering using the LLM service.
"""

import asyncio
import logging
import time
from typing import Optional
from datetime import datetime

from ..models.request_models import QuestionAnswerRequest
from ..models.response_models import QuestionAnswerResponse, ErrorResponse
from ..core.config import Settings
from ..core.resilience import with_circuit_breaker, ServiceUnavailableError, with_timeout

# Import LLM service components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from llm_service.core.service import LLMService
from llm_service.core.interfaces import LLMProvider
from llm_service.utils.exceptions import (
    LLMServiceError, LLMProviderError, LLMValidationError, 
    LLMRateLimitError, LLMConfigurationError
)

logger = logging.getLogger(__name__)


class QAService:
    """Service for handling general Q&A requests."""
    
    # Internal configuration - not exposed to users
    DEFAULT_MAX_WORDS = 200
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 300  # Roughly 1.5x max words
    
    def __init__(self, settings: Settings):
        """Initialize the Q&A service."""
        self.settings = settings
        self.llm_service: Optional[LLMService] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the LLM service."""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing LLM service for Q&A...")
            self.llm_service = LLMService()
            await self.llm_service.initialize()
            self._initialized = True
            logger.info("Q&A service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Q&A service: {e}")
            raise
    
    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())
    
    def _truncate_to_word_limit(self, text: str, max_words: int) -> str:
        """Truncate text to specified word limit."""
        words = text.split()
        if len(words) <= max_words:
            return text
        
        truncated = ' '.join(words[:max_words])
        # Add ellipsis if truncated
        if len(words) > max_words:
            truncated += "..."
        
        return truncated
    
    def _build_prompt(self, question: str) -> str:
        """Build the prompt for the LLM."""
        prompt = f"""You are a helpful AI assistant. Please provide a clear, accurate, and concise answer to the following question.

Requirements:
- Keep your answer to approximately {self.DEFAULT_MAX_WORDS} words or less
- Be informative and helpful
- Use clear, professional language
- If the question is unclear, make reasonable assumptions and state them
- Structure your answer with bullet points or numbered lists when appropriate
- Focus on the most important and practical information

Question: {question}

Answer:"""
        
        return prompt
    
    @with_circuit_breaker('llm_service')
    async def _call_llm_with_protection(self, prompt: str):
        """
        Call LLM service with circuit breaker protection and timeout.
        
        If the LLM service has failed multiple times, the circuit breaker
        will "open" and this method will fail immediately without making the call.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            LLM response object
            
        Raises:
            ServiceUnavailableError: If circuit breaker is open
            asyncio.TimeoutError: If call exceeds timeout
        """
        # Add timeout protection (30 seconds)
        return await with_timeout(
            self.llm_service.generate(
                prompt=prompt,
                temperature=self.DEFAULT_TEMPERATURE,
                max_tokens=self.DEFAULT_MAX_TOKENS,
                provider=LLMProvider.OPENAI
            ),
            timeout_seconds=30.0
        )
    
    async def answer_question(self, request: QuestionAnswerRequest) -> QuestionAnswerResponse:
        """
        Generate an answer to a user question.
        
        Args:
            request: The Q&A request containing question and parameters
            
        Returns:
            QuestionAnswerResponse with the generated answer
            
        Raises:
            Various LLM-related exceptions
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Build the prompt
            prompt = self._build_prompt(request.question)
            
            # Generate response using LLM service with internal defaults
            # Protected by circuit breaker and timeout
            logger.info(f"Generating answer for question: {request.question[:100]}...")
            
            llm_response = await self._call_llm_with_protection(prompt)
            
            # Extract and clean the answer
            answer = llm_response.content.strip()
            
            # Ensure word limit is respected
            if self._count_words(answer) > self.DEFAULT_MAX_WORDS:
                answer = self._truncate_to_word_limit(answer, self.DEFAULT_MAX_WORDS)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Build response
            response = QuestionAnswerResponse(
                question=request.question,
                answer=answer,
                word_count=self._count_words(answer),
                character_count=len(answer),
                ai_model=llm_response.model,
                processing_time_ms=processing_time,
                request_timestamp=datetime.utcnow()
            )
            
            logger.info(f"Generated answer in {processing_time:.1f}ms, {response.word_count} words")
            return response
            
        except ServiceUnavailableError as e:
            # Circuit breaker is open - service is temporarily unavailable
            logger.error(f"Circuit breaker OPEN for LLM service: {e}")
            raise Exception(
                f"AI service is temporarily unavailable due to repeated failures. "
                f"Circuit breaker is protecting the system. Please try again in a few moments."
            )
        
        except asyncio.TimeoutError:
            logger.error(f"LLM service call timed out after 30 seconds")
            raise Exception(
                f"AI service request timed out. The service may be overloaded. "
                f"Please try again with a simpler question."
            )
            
        except LLMValidationError as e:
            logger.error(f"Validation error: {e}")
            raise ValueError(f"Invalid request: {e}")
            
        except LLMRateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            raise Exception(f"Service temporarily unavailable due to rate limiting: {e}")
            
        except LLMProviderError as e:
            logger.error(f"Provider error: {e}")
            raise Exception(f"AI service error: {e}")
            
        except LLMConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise Exception(f"Service configuration error: {e}")
            
        except Exception as e:
            logger.error(f"Unexpected error in Q&A service: {e}")
            raise Exception(f"Failed to generate answer: {str(e)}")
    
    async def health_check(self) -> dict:
        """Check the health of the Q&A service."""
        if not self._initialized:
            return {
                "status": "not_initialized",
                "llm_service": "not_initialized"
            }
        
        try:
            # Check LLM service health
            llm_health = await self.llm_service.health_check()
            
            return {
                "status": "healthy" if llm_health["service"] == "healthy" else "degraded",
                "llm_service": llm_health["service"],
                "available_providers": list(llm_health["providers"].keys()),
                "healthy_providers": [
                    name for name, status in llm_health["providers"].items()
                    if status["status"] == "healthy"
                ]
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
