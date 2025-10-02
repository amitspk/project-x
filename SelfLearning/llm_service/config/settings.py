"""
Configuration settings for the LLM service module.

This module provides centralized configuration management with support for
environment variables, default values, and validation.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


@dataclass
class ProviderConfig:
    """Configuration for a specific LLM provider."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    max_retries: int = 3
    timeout: int = 60
    rate_limit_rpm: Optional[int] = None  # Requests per minute
    additional_headers: Dict[str, str] = field(default_factory=dict)
    custom_params: Dict[str, any] = field(default_factory=dict)


@dataclass
class LLMServiceConfig:
    """Main configuration for the LLM service."""
    
    # Default provider settings
    default_provider: str = "openai"
    default_temperature: float = 0.7
    default_max_tokens: Optional[int] = None
    
    # Provider configurations
    openai: ProviderConfig = field(default_factory=lambda: ProviderConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        default_model="gpt-3.5-turbo",
        rate_limit_rpm=3000
    ))
    
    anthropic: ProviderConfig = field(default_factory=lambda: ProviderConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        default_model="claude-3-sonnet-20240229",
        rate_limit_rpm=1000
    ))
    
    google: ProviderConfig = field(default_factory=lambda: ProviderConfig(
        api_key=os.getenv("GOOGLE_API_KEY"),
        base_url=os.getenv("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1"),
        default_model="gemini-pro",
        rate_limit_rpm=60
    ))
    
    ollama: ProviderConfig = field(default_factory=lambda: ProviderConfig(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        default_model="llama2",
        rate_limit_rpm=None  # No rate limit for local
    ))
    
    # Global settings
    enable_logging: bool = True
    log_level: str = "INFO"
    log_requests: bool = False  # Log full requests (be careful with sensitive data)
    log_responses: bool = False  # Log full responses
    
    # Retry and timeout settings
    global_timeout: int = 120
    global_max_retries: int = 3
    retry_delay: float = 1.0  # Base delay between retries
    exponential_backoff: bool = True
    
    # Caching settings
    enable_caching: bool = False
    cache_ttl: int = 3600  # Cache TTL in seconds
    cache_max_size: int = 1000  # Maximum number of cached responses
    
    # Safety and validation
    max_prompt_length: int = 100000  # Maximum prompt length
    max_response_length: int = 50000  # Maximum response length
    content_filter: bool = True  # Enable content filtering
    
    # Output settings
    default_output_format: str = "text"  # "text", "json", "markdown"
    include_usage_stats: bool = True
    include_metadata: bool = True
    
    @classmethod
    def from_env(cls) -> 'LLMServiceConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Override defaults with environment variables
        config.default_provider = os.getenv("LLM_DEFAULT_PROVIDER", config.default_provider)
        config.default_temperature = float(os.getenv("LLM_DEFAULT_TEMPERATURE", config.default_temperature))
        
        if os.getenv("LLM_DEFAULT_MAX_TOKENS"):
            config.default_max_tokens = int(os.getenv("LLM_DEFAULT_MAX_TOKENS"))
        
        config.enable_logging = os.getenv("LLM_ENABLE_LOGGING", "true").lower() == "true"
        config.log_level = os.getenv("LLM_LOG_LEVEL", config.log_level)
        config.global_timeout = int(os.getenv("LLM_GLOBAL_TIMEOUT", config.global_timeout))
        config.global_max_retries = int(os.getenv("LLM_GLOBAL_MAX_RETRIES", config.global_max_retries))
        
        return config
    
    def get_provider_config(self, provider: str) -> ProviderConfig:
        """Get configuration for a specific provider."""
        provider_configs = {
            "openai": self.openai,
            "anthropic": self.anthropic,
            "google": self.google,
            "ollama": self.ollama
        }
        
        if provider not in provider_configs:
            raise ValueError(f"Unknown provider: {provider}")
        
        return provider_configs[provider]
    
    def validate(self) -> List[str]:
        """Validate the configuration and return any errors."""
        errors = []
        
        # Check if at least one provider has valid configuration
        valid_providers = []
        
        if self.openai.api_key:
            valid_providers.append("openai")
        if self.anthropic.api_key:
            valid_providers.append("anthropic")
        if self.google.api_key:
            valid_providers.append("google")
        if self.ollama.base_url:  # Ollama doesn't need API key
            valid_providers.append("ollama")
        
        if not valid_providers:
            errors.append("No valid provider configurations found. Please set API keys or configure Ollama.")
        
        # Check if default provider is valid
        if self.default_provider not in valid_providers:
            errors.append(f"Default provider '{self.default_provider}' is not properly configured.")
        
        # Validate numeric ranges
        if not 0 <= self.default_temperature <= 2:
            errors.append("Temperature must be between 0 and 2.")
        
        if self.default_max_tokens is not None and self.default_max_tokens <= 0:
            errors.append("Max tokens must be positive.")
        
        if self.global_timeout <= 0:
            errors.append("Global timeout must be positive.")
        
        if self.global_max_retries < 0:
            errors.append("Max retries must be non-negative.")
        
        return errors
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Skip validation during import to allow graceful handling
        pass


# Global configuration instance
config = LLMServiceConfig.from_env()
