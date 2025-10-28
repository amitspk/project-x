"""
LLM Service Module

A production-grade LLM service that provides unified access to multiple
LLM providers including OpenAI, Anthropic, Google, and local models.

Features:
- Multiple LLM provider support (OpenAI, Anthropic, Google, Ollama)
- Async/await support for high performance
- Rate limiting and quota management
- Comprehensive error handling and retry logic
- Streaming response support
- Configuration management with environment variables
- Production-ready logging and monitoring
- Type hints and comprehensive documentation

Example usage:
    from llm_service import LLMService, LLMProvider
    
    # Initialize service
    service = LLMService()
    await service.initialize()
    
    # Generate response
    response = await service.generate("What is machine learning?")
    print(response.content)
    
    # Use specific provider
    response = await service.generate(
        "Explain quantum computing",
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-sonnet-20240229"
    )
    
    # Streaming response
    async for chunk in service.stream_generate("Tell me a story"):
        print(chunk, end="")
"""

from .core.service import LLMService
from .core.interfaces import (
    LLMProvider, LLMMessage, LLMResponse, LLMRequest,
    ILLMProvider, ILLMService
)
from .config.settings import LLMServiceConfig, ProviderConfig
from .utils.exceptions import (
    LLMServiceError, LLMProviderError, LLMAuthenticationError,
    LLMRateLimitError, LLMQuotaExceededError, LLMModelNotFoundError,
    LLMInvalidRequestError, LLMNetworkError, LLMTimeoutError,
    LLMConfigurationError, LLMValidationError
)

# Version information
__version__ = "1.0.0"
__author__ = "Senior Software Engineer"
__description__ = "Production-grade LLM service with multi-provider support"

# Public API
__all__ = [
    # Main service class
    "LLMService",
    
    # Core interfaces and data classes
    "LLMProvider",
    "LLMMessage", 
    "LLMResponse",
    "LLMRequest",
    "ILLMProvider",
    "ILLMService",
    
    # Configuration
    "LLMServiceConfig",
    "ProviderConfig",
    
    # Exceptions
    "LLMServiceError",
    "LLMProviderError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMQuotaExceededError",
    "LLMModelNotFoundError",
    "LLMInvalidRequestError",
    "LLMNetworkError",
    "LLMTimeoutError",
    "LLMConfigurationError",
    "LLMValidationError",
    
    # Version info
    "__version__",
    "__author__",
    "__description__"
]
