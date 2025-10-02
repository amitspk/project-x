"""
Anthropic Claude LLM provider implementation.

This module provides integration with Anthropic's Claude API.
"""

import asyncio
import logging
from typing import List, AsyncGenerator, Optional, Dict, Any
import json

try:
    import anthropic
    from anthropic import AsyncAnthropic
except ImportError:
    anthropic = None
    AsyncAnthropic = None

from ..core.interfaces import ILLMProvider, LLMRequest, LLMResponse, LLMMessage
from ..utils.exceptions import (
    LLMProviderError, LLMAuthenticationError, LLMRateLimitError,
    LLMQuotaExceededError, LLMModelNotFoundError, LLMInvalidRequestError,
    LLMNetworkError, LLMTimeoutError
)
from ..config.settings import ProviderConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(ILLMProvider):
    """Anthropic Claude LLM provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize the Anthropic provider.
        
        Args:
            config: Provider configuration
            
        Raises:
            LLMProviderError: If Anthropic library is not installed or configuration is invalid
        """
        if anthropic is None:
            raise LLMProviderError(
                "Anthropic library not installed. Please install with: pip install anthropic",
                provider="anthropic"
            )
        
        if not config.api_key:
            raise LLMAuthenticationError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable.",
                provider="anthropic"
            )
        
        self.config = config
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        
        # Available models
        self._available_models = [
            "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
            "claude-2.1", "claude-2.0", "claude-instant-1.2"
        ]
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "anthropic"
    
    @property
    def default_model(self) -> str:
        """Get the default model."""
        return self.config.default_model or "claude-3-sonnet-20240229"
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return self._available_models.copy()
    
    async def validate_connection(self) -> bool:
        """Validate connection to Anthropic API."""
        try:
            # Try a simple completion as a connection test
            test_response = await self.client.messages.create(
                model=self.default_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            logger.info("Anthropic connection validated successfully.")
            return True
        except Exception as e:
            logger.error(f"Anthropic connection validation failed: {e}")
            return False
    
    def _convert_messages(self, messages: List[LLMMessage]) -> tuple[List[Dict[str, str]], Optional[str]]:
        """
        Convert LLMMessage objects to Anthropic format.
        
        Returns:
            Tuple of (messages, system_prompt)
        """
        system_prompt = None
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == "system":
                # Anthropic handles system messages separately
                system_prompt = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return anthropic_messages, system_prompt
    
    def _handle_anthropic_error(self, error: Exception) -> None:
        """Convert Anthropic errors to our custom exceptions."""
        error_message = str(error)
        
        if hasattr(error, 'status_code'):
            status_code = error.status_code
            
            if status_code == 401:
                raise LLMAuthenticationError(
                    f"Anthropic authentication failed: {error_message}",
                    provider="anthropic"
                )
            elif status_code == 429:
                raise LLMRateLimitError(
                    f"Anthropic rate limit exceeded: {error_message}",
                    provider="anthropic"
                )
            elif status_code == 402:
                raise LLMQuotaExceededError(
                    f"Anthropic quota exceeded: {error_message}",
                    provider="anthropic"
                )
            elif status_code == 404:
                raise LLMModelNotFoundError(
                    f"Anthropic model not found: {error_message}",
                    provider="anthropic"
                )
            elif status_code == 400:
                raise LLMInvalidRequestError(
                    f"Anthropic invalid request: {error_message}",
                    provider="anthropic"
                )
        
        if "timeout" in error_message.lower():
            raise LLMTimeoutError(
                f"Anthropic request timeout: {error_message}",
                provider="anthropic"
            )
        elif "network" in error_message.lower() or "connection" in error_message.lower():
            raise LLMNetworkError(
                f"Anthropic network error: {error_message}",
                provider="anthropic"
            )
        else:
            raise LLMProviderError(
                f"Anthropic error: {error_message}",
                provider="anthropic"
            )
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using Anthropic API."""
        try:
            # Convert messages
            messages, system_from_messages = self._convert_messages(request.messages)
            
            # Use system prompt from request or extracted from messages
            system_prompt = request.system_prompt or system_from_messages
            
            # Prepare request parameters
            params = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,  # Anthropic requires max_tokens
                "temperature": request.temperature,
                "stream": False
            }
            
            if system_prompt:
                params["system"] = system_prompt
            
            # Add any additional parameters
            if request.additional_params:
                params.update(request.additional_params)
            
            logger.debug(f"Sending Anthropic request: model={request.model}, messages={len(messages)}")
            
            # Make the API call
            response = await self.client.messages.create(**params)
            
            # Extract response data
            content = response.content[0].text if response.content else ""
            finish_reason = response.stop_reason
            
            # Extract usage information
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            
            logger.info(f"Anthropic response generated: {len(content)} characters")
            
            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=request.model,
                usage=usage,
                finish_reason=finish_reason,
                metadata={
                    "response_id": response.id if hasattr(response, 'id') else None,
                    "model_version": response.model if hasattr(response, 'model') else None
                }
            )
            
        except Exception as e:
            logger.error(f"Anthropic request failed: {e}")
            self._handle_anthropic_error(e)
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate a streaming response using Anthropic API."""
        try:
            # Convert messages
            messages, system_from_messages = self._convert_messages(request.messages)
            
            # Use system prompt from request or extracted from messages
            system_prompt = request.system_prompt or system_from_messages
            
            # Prepare request parameters
            params = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,  # Anthropic requires max_tokens
                "temperature": request.temperature,
                "stream": True
            }
            
            if system_prompt:
                params["system"] = system_prompt
            
            # Add any additional parameters
            if request.additional_params:
                params.update(request.additional_params)
            
            logger.debug(f"Starting Anthropic stream: model={request.model}, messages={len(messages)}")
            
            # Make the streaming API call
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
            
            logger.info("Anthropic stream completed")
            
        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            self._handle_anthropic_error(e)
