"""
LLM Model Configuration - Model to Provider Mappings

This file contains ONLY configuration mappings.
To add new models or providers, modify the dictionaries below.

DO NOT modify the factory.py file - only modify this model_config file.
"""


class LLMModelConfig:
    """
    Configuration class for model-to-provider mappings.
    
    This is a pure configuration class. All model-to-provider mappings
    are defined here. To add new models, simply add them to the dictionaries below.
    """
    
    # ========================================================================
    # DEFAULT MODEL
    # ========================================================================
    # Default model used when no model is explicitly specified
    
    DEFAULT_MODEL = "gpt-4o-mini"
    
    # ========================================================================
    # DEFAULT EMBEDDING MODEL
    # ========================================================================
    # Default embedding model used for vector embeddings (OpenAI only)
    
    DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
    
    # ========================================================================
    # DEFAULT TEMPERATURE
    # ========================================================================
    # Default temperature used when no temperature is explicitly specified
    
    DEFAULT_TEMPERATURE = 0.7
    
    # ========================================================================
    # DEFAULT MAX TOKENS
    # ========================================================================
    # Default max_tokens used when no max_tokens is explicitly specified
    # Operation-specific defaults for different use cases
    
    DEFAULT_MAX_TOKENS_SUMMARY = 2000
    DEFAULT_MAX_TOKENS_QUESTIONS = 4000  # Higher for detailed Q&A generation
    DEFAULT_MAX_TOKENS_CHAT = 300
    
    # ========================================================================
    # EXACT MODEL-TO-PROVIDER MAPPINGS
    # ========================================================================
    # Add exact model name mappings here for explicit routing
    
    MODEL_TO_PROVIDER = {
        # OpenAI Chat models
        "gpt-4o-mini": "openai",
        "gpt-4o": "openai",
        "gpt-4": "openai",
        "gpt-3.5-turbo": "openai",
        "gpt-3.5": "openai",
        
        # OpenAI Embedding models
        "text-embedding-3-small": "openai",
        "text-embedding-3-large": "openai",
        "text-embedding-ada-002": "openai",
        
        # Anthropic models
        "claude-3-5-sonnet-20241022": "anthropic",
        "claude-3-5-haiku-20241022": "anthropic",
        "claude-3-5-sonnet": "anthropic",
        "claude-3-5-haiku": "anthropic",
        "claude-3-sonnet": "anthropic",
        "claude-3-haiku": "anthropic",
        "claude-3-opus": "anthropic",
    }
    
    # ========================================================================
    # PREFIX-TO-PROVIDER MAPPINGS (Fallback)
    # ========================================================================
    # Used when exact model name is not found
    # Ordered by specificity (most specific first)
    
    PREFIX_TO_PROVIDER = {
        "gpt-4": "openai",
        "gpt-3.5": "openai",
        "gpt-": "openai",
        "text-embedding-": "openai",
        "claude-": "anthropic",
    }

