"""Factory for creating LLM providers based on model name."""

import logging
import os
from typing import Optional
from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .model_config import LLMModelConfig

logger = logging.getLogger(__name__)


class LLMProviderConfigManager:
    """
    Manager class for model-to-provider routing logic.
    
    This class uses the configuration from LLMModelConfig (in model_config.py)
    to route models to providers. The actual mappings are defined in model_config.py.
    
    To add new models, edit model_config.py - DO NOT modify this file.
    """
    
    def __init__(self):
        # Load configuration from model_config.py
        self._model_to_provider = LLMModelConfig.MODEL_TO_PROVIDER.copy()
        self._prefix_to_provider = LLMModelConfig.PREFIX_TO_PROVIDER.copy()
    
    def get_provider_for_model(self, model: str) -> str:
        """
        Identify which provider to use based on model name.
        
        Uses exact match first, then falls back to prefix matching.
        
        Args:
            model: Model identifier (e.g., "gpt-4o-mini", "claude-3-5-sonnet-20241022")
            
        Returns:
            Provider name: "openai", "anthropic", "gemini", etc.
            
        Raises:
            ValueError: If model is not recognized
        """
        model_lower = model.lower()
        
        # First, try exact match in configuration map
        if model_lower in self._model_to_provider:
            provider = self._model_to_provider[model_lower]
            logger.debug(f"📋 Exact match found: {model} -> {provider}")
            return provider
        
        # Fallback: Try prefix-based matching (ordered by specificity)
        for prefix, provider in self._prefix_to_provider.items():
            if model_lower.startswith(prefix):
                logger.debug(f"📋 Prefix match found: {model} (starts with '{prefix}') -> {provider}")
                return provider
        
        # No match found
        supported_models = ", ".join(sorted(set(self._model_to_provider.keys())))
        supported_prefixes = ", ".join(sorted(self._prefix_to_provider.keys()))
        raise ValueError(
            f"Unknown model: {model}. "
            f"Supported models: {supported_models}. "
            f"Or use models starting with: {supported_prefixes}"
        )
    
    def add_model(self, model: str, provider: str) -> None:
        """
        Add a new model-to-provider mapping.
        
        Args:
            model: Model identifier (will be lowercased)
            provider: Provider name ("openai", "anthropic", "gemini", etc.)
        """
        self._model_to_provider[model.lower()] = provider.lower()
        logger.info(f"✅ Added model mapping: {model} -> {provider}")
    
    def add_prefix(self, prefix: str, provider: str) -> None:
        """
        Add a new prefix-to-provider mapping.
        
        Args:
            prefix: Model prefix (e.g., "gpt-", "claude-", "gemini-")
            provider: Provider name ("openai", "anthropic", etc.)
        """
        self._prefix_to_provider[prefix.lower()] = provider.lower()
        logger.info(f"✅ Added prefix mapping: {prefix} -> {provider}")
    
    def get_all_models(self) -> dict:
        """Get all configured model mappings."""
        return self._model_to_provider.copy()
    
    def get_all_prefixes(self) -> dict:
        """Get all configured prefix mappings."""
        return self._prefix_to_provider.copy()


# Global configuration manager instance (singleton pattern)
_provider_config = LLMProviderConfigManager()


def get_provider_config() -> LLMProviderConfigManager:
    """
    Get the global LLM provider configuration manager instance.
    
    Use this to modify model-to-provider mappings at runtime:
    
    Example:
        config = get_provider_config()
        config.add_model("gpt-5", "openai")
        config.add_prefix("gemini-", "gemini")
    
    Returns:
        LLMProviderConfigManager instance
    """
    return _provider_config


def get_provider_for_model(model: str) -> str:
    """
    Identify which provider to use based on model name.
    
    Delegates to LLMProviderConfig for routing logic.
    
    Args:
        model: Model identifier (e.g., "gpt-4o-mini", "claude-3-5-sonnet-20241022")
        
    Returns:
        Provider name: "openai", "anthropic", "gemini", etc.
        
    Raises:
        ValueError: If model is not recognized
    """
    return _provider_config.get_provider_for_model(model)


def get_api_key_for_provider(provider: str, model: Optional[str] = None) -> str:
    """
    Get API key for the specified provider.
    
    Args:
        provider: Provider name ("openai", "anthropic", "gemini", etc.)
        model: Optional model name for fallback logic
        
    Returns:
        API key string
        
    Raises:
        ValueError: If API key is not found
    """
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for OpenAI models"
            )
        return api_key
    
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for Anthropic models"
            )
        return api_key
    
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is required for Gemini models"
            )
        return api_key
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    @staticmethod
    def create(
        model: str,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS,
        embedding_model: Optional[str] = None
    ) -> LLMProvider:
        """
        Create an LLM provider instance for the specified model.
        
        Args:
            model: Model identifier (e.g., "gpt-4o-mini", "claude-3-5-sonnet-20241022")
            api_key: Optional API key (if not provided, fetched from env vars)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            embedding_model: Optional embedding model override. If None, a provider-specific default is used.
            
        Returns:
            LLMProvider instance
            
        Raises:
            ValueError: If model is not recognized or API key is missing
        """
        provider = get_provider_for_model(model)
        logger.info(f"🔍 Model '{model}' routed to provider: {provider}")
        
        # Apply provider-specific defaults
        if embedding_model is None:
            if provider == "openai":
                embedding_model = LLMModelConfig.DEFAULT_EMBEDDING_MODEL
            elif provider == "gemini":
                embedding_model = LLMModelConfig.DEFAULT_GEMINI_EMBEDDING_MODEL
        
        # Get API key
        if not api_key:
            api_key = get_api_key_for_provider(provider, model)
        
        # Create provider instance
        if provider == "openai":
            return OpenAIProvider(
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                embedding_model=embedding_model
            )
        
        elif provider == "anthropic":
            # Anthropic doesn't use embedding_model parameter
            return AnthropicProvider(
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        elif provider == "gemini":
            return GeminiProvider(
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                embedding_model=embedding_model
            )
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")

