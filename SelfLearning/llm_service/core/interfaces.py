"""
Abstract base classes and interfaces for LLM service providers.

This module defines the contracts that all LLM providers must implement,
ensuring consistent behavior across different LLM services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


@dataclass
class LLMMessage:
    """Represents a message in an LLM conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """Represents a response from an LLM provider."""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


@dataclass
class LLMRequest:
    """Represents a request to an LLM provider."""
    messages: List[LLMMessage]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    system_prompt: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None


class ILLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from the LLM provider.
        
        Args:
            request: The LLM request containing messages and parameters
            
        Returns:
            LLMResponse containing the generated content and metadata
            
        Raises:
            LLMProviderError: If the request fails
        """
        pass
    
    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM provider.
        
        Args:
            request: The LLM request containing messages and parameters
            
        Yields:
            str: Chunks of the generated response
            
        Raises:
            LLMProviderError: If the request fails
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate the connection to the LLM provider.
        
        Returns:
            bool: True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models for this provider.
        
        Returns:
            List[str]: Available model names
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Get the default model for this provider."""
        pass


class ILLMService(ABC):
    """Abstract base class for LLM service orchestrator."""
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response using the specified or default provider.
        
        Args:
            prompt: The input prompt
            provider: Optional specific provider to use
            model: Optional specific model to use
            **kwargs: Additional parameters for the request
            
        Returns:
            LLMResponse containing the generated content
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from a conversation history.
        
        Args:
            messages: List of conversation messages
            provider: Optional specific provider to use
            model: Optional specific model to use
            **kwargs: Additional parameters for the request
            
        Returns:
            LLMResponse containing the generated content
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response.
        
        Args:
            prompt: The input prompt
            provider: Optional specific provider to use
            model: Optional specific model to use
            **kwargs: Additional parameters for the request
            
        Yields:
            str: Chunks of the generated response
        """
        pass
