"""
OpenAI LLM provider implementation.

This module provides integration with OpenAI's API, including GPT models
and other OpenAI services.
"""

import asyncio
import logging
from typing import List, AsyncGenerator, Optional, Dict, Any
import json

try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None
    AsyncOpenAI = None

from ..core.interfaces import ILLMProvider, LLMRequest, LLMResponse, LLMMessage
from ..utils.exceptions import (
    LLMProviderError, LLMAuthenticationError, LLMRateLimitError,
    LLMQuotaExceededError, LLMModelNotFoundError, LLMInvalidRequestError,
    LLMNetworkError, LLMTimeoutError
)
from ..config.settings import ProviderConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(ILLMProvider):
    """OpenAI LLM provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize the OpenAI provider.
        
        Args:
            config: Provider configuration
            
        Raises:
            LLMProviderError: If OpenAI library is not installed or configuration is invalid
        """
        if openai is None:
            raise LLMProviderError(
                "OpenAI library not installed. Please install with: pip install openai",
                provider="openai"
            )
        
        if not config.api_key:
            raise LLMAuthenticationError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable.",
                provider="openai"
            )
        
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        
        # Available models (can be updated via API call)
        self._available_models = [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-4-32k",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-instruct"
        ]
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "openai"
    
    @property
    def default_model(self) -> str:
        """Get the default model."""
        return self.config.default_model or "gpt-3.5-turbo"
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return self._available_models.copy()
    
    async def validate_connection(self) -> bool:
        """Validate connection to OpenAI API."""
        try:
            # Try to list models as a connection test
            models = await self.client.models.list()
            self._available_models = [model.id for model in models.data if model.id.startswith(('gpt-', 'text-'))]
            logger.info(f"OpenAI connection validated. Found {len(self._available_models)} models.")
            return True
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False
    
    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """Convert LLMMessage objects to OpenAI format."""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def _handle_openai_error(self, error: Exception) -> None:
        """Convert OpenAI errors to our custom exceptions."""
        error_message = str(error)
        
        if hasattr(error, 'status_code'):
            status_code = error.status_code
            
            if status_code == 401:
                raise LLMAuthenticationError(
                    f"OpenAI authentication failed: {error_message}",
                    provider="openai"
                )
            elif status_code == 429:
                raise LLMRateLimitError(
                    f"OpenAI rate limit exceeded: {error_message}",
                    provider="openai"
                )
            elif status_code == 402:
                raise LLMQuotaExceededError(
                    f"OpenAI quota exceeded: {error_message}",
                    provider="openai"
                )
            elif status_code == 404:
                raise LLMModelNotFoundError(
                    f"OpenAI model not found: {error_message}",
                    provider="openai"
                )
            elif status_code == 400:
                raise LLMInvalidRequestError(
                    f"OpenAI invalid request: {error_message}",
                    provider="openai"
                )
        
        if "timeout" in error_message.lower():
            raise LLMTimeoutError(
                f"OpenAI request timeout: {error_message}",
                provider="openai"
            )
        elif "network" in error_message.lower() or "connection" in error_message.lower():
            raise LLMNetworkError(
                f"OpenAI network error: {error_message}",
                provider="openai"
            )
        else:
            raise LLMProviderError(
                f"OpenAI error: {error_message}",
                provider="openai"
            )
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using OpenAI API."""
        try:
            # Prepare messages
            messages = self._convert_messages(request.messages)
            
            # Add system prompt if provided
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            # Prepare request parameters
            params = {
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature,
                "stream": False
            }
            
            if request.max_tokens:
                params["max_tokens"] = request.max_tokens
            
            # Add any additional parameters
            if request.additional_params:
                params.update(request.additional_params)
            
            logger.debug(f"Sending OpenAI request: model={request.model}, messages={len(messages)}")
            
            # Make the API call
            response = await self.client.chat.completions.create(**params)
            
            # Extract response data
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            # Extract usage information
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            logger.info(f"OpenAI response generated: {len(content)} characters")
            
            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=request.model,
                usage=usage,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id if hasattr(response, 'id') else None,
                    "created": response.created if hasattr(response, 'created') else None
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            self._handle_openai_error(e)
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming response using OpenAI API."""
        try:
            # Prepare messages
            messages = self._convert_messages(request.messages)
            
            # Add system prompt if provided
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            # Prepare request parameters
            params = {
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature,
                "stream": True
            }
            
            if request.max_tokens:
                params["max_tokens"] = request.max_tokens
            
            # Add any additional parameters
            if request.additional_params:
                params.update(request.additional_params)
            
            logger.debug(f"Starting OpenAI stream: model={request.model}, messages={len(messages)}")
            
            # Make the streaming API call
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info("OpenAI stream completed")
            
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            self._handle_openai_error(e)
