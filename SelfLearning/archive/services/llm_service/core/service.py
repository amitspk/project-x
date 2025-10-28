"""
Main LLM service orchestrator.

This module provides the main LLMService class that coordinates between
different LLM providers and provides a unified interface for LLM operations.
"""

import asyncio
import logging
from typing import Dict, Optional, List, AsyncGenerator, Any
from datetime import datetime, timedelta
import time

from .interfaces import ILLMService, ILLMProvider, LLMProvider, LLMRequest, LLMResponse, LLMMessage
from ..providers.openai_provider import OpenAIProvider
from ..providers.anthropic_provider import AnthropicProvider
from ..config.settings import LLMServiceConfig, ProviderConfig
from ..utils.exceptions import (
    LLMServiceError, LLMProviderError, LLMConfigurationError,
    LLMValidationError, LLMRateLimitError
)

logger = logging.getLogger(__name__)


class LLMService(ILLMService):
    """Main LLM service orchestrator."""
    
    def __init__(self, config: Optional[LLMServiceConfig] = None):
        """
        Initialize the LLM service.
        
        Args:
            config: Optional configuration. If not provided, uses default config.
        """
        self.config = config or LLMServiceConfig.from_env()
        self.providers: Dict[str, ILLMProvider] = {}
        self._rate_limiters: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        
        # Initialize logging
        if self.config.enable_logging:
            self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def initialize(self):
        """Initialize all configured providers."""
        if self._initialized:
            return
        
        logger.info("Initializing LLM service...")
        
        # Initialize providers based on configuration
        await self._initialize_providers()
        
        # Validate at least one provider is available
        if not self.providers:
            raise LLMConfigurationError("No LLM providers could be initialized")
        
        # Validate default provider
        if self.config.default_provider not in self.providers:
            available = list(self.providers.keys())
            logger.warning(f"Default provider '{self.config.default_provider}' not available. Using '{available[0]}'")
            self.config.default_provider = available[0]
        
        self._initialized = True
        logger.info(f"LLM service initialized with providers: {list(self.providers.keys())}")
    
    async def _initialize_providers(self):
        """Initialize all configured LLM providers."""
        provider_configs = {
            "openai": (self.config.openai, OpenAIProvider),
            "anthropic": (self.config.anthropic, AnthropicProvider),
            # Add more providers here as they're implemented
        }
        
        for provider_name, (config, provider_class) in provider_configs.items():
            try:
                # Skip if no API key (except for local providers like Ollama)
                if provider_name != "ollama" and not config.api_key:
                    logger.debug(f"Skipping {provider_name}: no API key configured")
                    continue
                
                # Initialize provider
                provider = provider_class(config)
                
                # Validate connection
                if await provider.validate_connection():
                    self.providers[provider_name] = provider
                    self._rate_limiters[provider_name] = {
                        "requests": [],
                        "rpm_limit": config.rate_limit_rpm
                    }
                    logger.info(f"Initialized {provider_name} provider")
                else:
                    logger.warning(f"Failed to validate {provider_name} provider connection")
                    
            except Exception as e:
                logger.error(f"Failed to initialize {provider_name} provider: {e}")
    
    def _validate_prompt(self, prompt: str) -> None:
        """Validate prompt input."""
        if not prompt or not prompt.strip():
            raise LLMValidationError("Prompt cannot be empty")
        
        if len(prompt) > self.config.max_prompt_length:
            raise LLMValidationError(
                f"Prompt too long: {len(prompt)} > {self.config.max_prompt_length}"
            )
    
    def _validate_messages(self, messages: List[LLMMessage]) -> None:
        """Validate message list."""
        if not messages:
            raise LLMValidationError("Messages list cannot be empty")
        
        total_length = sum(len(msg.content) for msg in messages)
        if total_length > self.config.max_prompt_length:
            raise LLMValidationError(
                f"Total messages too long: {total_length} > {self.config.max_prompt_length}"
            )
    
    async def _check_rate_limit(self, provider_name: str) -> None:
        """Check and enforce rate limits for a provider."""
        if provider_name not in self._rate_limiters:
            return
        
        rate_limiter = self._rate_limiters[provider_name]
        rpm_limit = rate_limiter["rpm_limit"]
        
        if rpm_limit is None:
            return  # No rate limit
        
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        rate_limiter["requests"] = [
            req_time for req_time in rate_limiter["requests"] 
            if req_time > minute_ago
        ]
        
        # Check if we're at the limit
        if len(rate_limiter["requests"]) >= rpm_limit:
            raise LLMRateLimitError(
                f"Rate limit exceeded for {provider_name}: {rpm_limit} requests per minute",
                provider=provider_name
            )
        
        # Record this request
        rate_limiter["requests"].append(now)
    
    def _get_provider(self, provider: Optional[LLMProvider] = None) -> ILLMProvider:
        """Get the specified provider or default provider."""
        if not self._initialized:
            raise LLMServiceError("LLM service not initialized. Call initialize() first.")
        
        provider_name = provider.value if provider else self.config.default_provider
        
        if provider_name not in self.providers:
            available = list(self.providers.keys())
            raise LLMProviderError(
                f"Provider '{provider_name}' not available. Available: {available}",
                provider=provider_name
            )
        
        return self.providers[provider_name]
    
    async def generate(
        self, 
        prompt: str, 
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using the specified or default provider."""
        # Validate input
        self._validate_prompt(prompt)
        
        # Get provider
        llm_provider = self._get_provider(provider)
        
        # Check rate limits
        await self._check_rate_limit(llm_provider.provider_name)
        
        # Prepare request
        messages = [LLMMessage(role="user", content=prompt)]
        
        request = LLMRequest(
            messages=messages,
            model=model or llm_provider.default_model,
            temperature=temperature or self.config.default_temperature,
            max_tokens=max_tokens or self.config.default_max_tokens,
            system_prompt=system_prompt,
            additional_params=kwargs
        )
        
        logger.info(f"Generating response with {llm_provider.provider_name} ({request.model})")
        
        try:
            response = await llm_provider.generate_response(request)
            
            # Validate response length
            if len(response.content) > self.config.max_response_length:
                logger.warning(f"Response truncated: {len(response.content)} > {self.config.max_response_length}")
                response.content = response.content[:self.config.max_response_length]
            
            return response
            
        except Exception as e:
            logger.error(f"Generation failed with {llm_provider.provider_name}: {e}")
            raise
    
    async def chat(
        self,
        messages: List[LLMMessage],
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from a conversation history."""
        # Validate input
        self._validate_messages(messages)
        
        # Get provider
        llm_provider = self._get_provider(provider)
        
        # Check rate limits
        await self._check_rate_limit(llm_provider.provider_name)
        
        # Prepare request
        request = LLMRequest(
            messages=messages,
            model=model or llm_provider.default_model,
            temperature=temperature or self.config.default_temperature,
            max_tokens=max_tokens or self.config.default_max_tokens,
            system_prompt=system_prompt,
            additional_params=kwargs
        )
        
        logger.info(f"Generating chat response with {llm_provider.provider_name} ({request.model})")
        
        try:
            response = await llm_provider.generate_response(request)
            
            # Validate response length
            if len(response.content) > self.config.max_response_length:
                logger.warning(f"Response truncated: {len(response.content)} > {self.config.max_response_length}")
                response.content = response.content[:self.config.max_response_length]
            
            return response
            
        except Exception as e:
            logger.error(f"Chat generation failed with {llm_provider.provider_name}: {e}")
            raise
    
    async def stream_generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        # Validate input
        self._validate_prompt(prompt)
        
        # Get provider
        llm_provider = self._get_provider(provider)
        
        # Check rate limits
        await self._check_rate_limit(llm_provider.provider_name)
        
        # Prepare request
        messages = [LLMMessage(role="user", content=prompt)]
        
        request = LLMRequest(
            messages=messages,
            model=model or llm_provider.default_model,
            temperature=temperature or self.config.default_temperature,
            max_tokens=max_tokens or self.config.default_max_tokens,
            system_prompt=system_prompt,
            stream=True,
            additional_params=kwargs
        )
        
        logger.info(f"Starting stream generation with {llm_provider.provider_name} ({request.model})")
        
        try:
            total_length = 0
            async for chunk in llm_provider.generate_stream(request):
                total_length += len(chunk)
                
                # Check response length limit
                if total_length > self.config.max_response_length:
                    logger.warning(f"Stream truncated at {total_length} characters")
                    break
                
                yield chunk
                
        except Exception as e:
            logger.error(f"Stream generation failed with {llm_provider.provider_name}: {e}")
            raise
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return list(self.providers.keys())
    
    def get_provider_models(self, provider: Optional[LLMProvider] = None) -> List[str]:
        """Get available models for a provider."""
        llm_provider = self._get_provider(provider)
        return llm_provider.get_available_models()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all providers."""
        if not self._initialized:
            await self.initialize()
        
        health_status = {
            "service": "healthy",
            "providers": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for name, provider in self.providers.items():
            try:
                is_healthy = await provider.validate_connection()
                health_status["providers"][name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "models": provider.get_available_models()
                }
            except Exception as e:
                health_status["providers"][name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Overall service health
        unhealthy_providers = [
            name for name, status in health_status["providers"].items()
            if status["status"] != "healthy"
        ]
        
        if len(unhealthy_providers) == len(self.providers):
            health_status["service"] = "unhealthy"
        elif unhealthy_providers:
            health_status["service"] = "degraded"
        
        return health_status
