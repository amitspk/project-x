"""
Custom exceptions for the LLM service module.

This module defines a hierarchy of exceptions specific to LLM operations,
providing clear error handling and debugging capabilities.
"""


class LLMServiceError(Exception):
    """Base exception for all LLM service related errors."""
    
    def __init__(self, message: str, provider: str = None, model: str = None):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.message = message
    
    def __str__(self):
        parts = [self.message]
        if self.provider:
            parts.append(f"Provider: {self.provider}")
        if self.model:
            parts.append(f"Model: {self.model}")
        return " | ".join(parts)


class LLMProviderError(LLMServiceError):
    """Raised when an LLM provider encounters an error."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication with an LLM provider fails."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class LLMQuotaExceededError(LLMProviderError):
    """Raised when usage quota is exceeded."""
    pass


class LLMModelNotFoundError(LLMProviderError):
    """Raised when a requested model is not available."""
    pass


class LLMInvalidRequestError(LLMProviderError):
    """Raised when the request parameters are invalid."""
    pass


class LLMNetworkError(LLMProviderError):
    """Raised when network connectivity issues occur."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when requests timeout."""
    pass


class LLMConfigurationError(LLMServiceError):
    """Raised when there are configuration issues."""
    pass


class LLMValidationError(LLMServiceError):
    """Raised when input validation fails."""
    pass
