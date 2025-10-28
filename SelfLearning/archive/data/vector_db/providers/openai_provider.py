"""
OpenAI embedding provider implementation.

This module provides integration with OpenAI's embedding models
for generating vector representations of text content.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
import numpy as np
from openai import AsyncOpenAI
from openai.types import CreateEmbeddingResponse

from ..core.interfaces import IEmbeddingProvider
from ..models.vector_models import EmbeddingRequest, EmbeddingModel
from ..utils.exceptions import EmbeddingError, ConfigurationError, RateLimitError

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(IEmbeddingProvider):
    """
    OpenAI embedding provider using the OpenAI API.
    
    Supports multiple OpenAI embedding models with configurable parameters
    and robust error handling including rate limiting and retries.
    """
    
    # Model configurations
    MODEL_CONFIGS = {
        EmbeddingModel.OPENAI_TEXT_EMBEDDING_ADA_002: {
            'name': 'text-embedding-ada-002',
            'dimension': 1536,
            'max_tokens': 8191,
            'cost_per_1k_tokens': 0.0001
        },
        EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL: {
            'name': 'text-embedding-3-small',
            'dimension': 1536,
            'max_tokens': 8191,
            'cost_per_1k_tokens': 0.00002
        },
        EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_LARGE: {
            'name': 'text-embedding-3-large',
            'dimension': 3072,
            'max_tokens': 8191,
            'cost_per_1k_tokens': 0.00013
        }
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: EmbeddingModel = EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL,
        max_retries: int = 3,
        timeout: float = 30.0,
        base_url: Optional[str] = None,
        organization: Optional[str] = None
    ):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key (if None, will use OPENAI_API_KEY env var)
            model: Embedding model to use
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
            base_url: Custom base URL for OpenAI API
            organization: OpenAI organization ID
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if model not in self.MODEL_CONFIGS:
            raise ConfigurationError(
                f"Unsupported model: {model}",
                config_key="model",
                config_value=str(model)
            )
        
        self._model = model
        self._model_config = self.MODEL_CONFIGS[model]
        self._max_retries = max_retries
        self._timeout = timeout
        
        try:
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                organization=organization,
                timeout=timeout,
                max_retries=max_retries
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize OpenAI client: {str(e)}",
                cause=e
            )
        
        logger.info(f"Initialized OpenAI embedding provider with model {self._model_config['name']}")
    
    @property
    def provider_name(self) -> str:
        """Get the name of the embedding provider."""
        return "openai"
    
    @property
    def model_name(self) -> str:
        """Get the name of the embedding model."""
        return self._model_config['name']
    
    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        return self._model_config['dimension']
    
    @property
    def max_tokens(self) -> int:
        """Get the maximum number of tokens supported by the model."""
        return self._model_config['max_tokens']
    
    async def generate_embedding(self, request: EmbeddingRequest) -> np.ndarray:
        """
        Generate embedding for a single text input.
        
        Args:
            request: Embedding request containing text and parameters
            
        Returns:
            Numpy array containing the embedding vector
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            # Validate input
            if not request.text.strip():
                raise EmbeddingError(
                    "Input text cannot be empty",
                    provider=self.provider_name,
                    model=self.model_name
                )
            
            # Check token limit (approximate)
            estimated_tokens = len(request.text.split()) * 1.3  # Rough estimate
            if estimated_tokens > self.max_tokens:
                raise EmbeddingError(
                    f"Input text too long: ~{estimated_tokens} tokens > {self.max_tokens}",
                    provider=self.provider_name,
                    model=self.model_name,
                    input_text_length=len(request.text)
                )
            
            # Make API request
            response = await self._make_embedding_request([request.text])
            
            # Extract embedding
            embedding_data = response.data[0].embedding
            embedding = np.array(embedding_data, dtype=np.float32)
            
            # Normalize if requested
            if request.normalize:
                embedding = self._normalize_embedding(embedding)
            
            logger.debug(f"Generated embedding for text of length {len(request.text)}")
            return embedding
            
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate embedding: {str(e)}",
                provider=self.provider_name,
                model=self.model_name,
                input_text_length=len(request.text),
                cause=e
            )
    
    async def generate_embeddings_batch(
        self,
        requests: List[EmbeddingRequest]
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple text inputs in batch.
        
        Args:
            requests: List of embedding requests
            
        Returns:
            List of numpy arrays containing embedding vectors
            
        Raises:
            EmbeddingError: If batch embedding generation fails
        """
        if not requests:
            return []
        
        try:
            # Extract texts and validate
            texts = []
            for i, request in enumerate(requests):
                if not request.text.strip():
                    raise EmbeddingError(
                        f"Input text at index {i} cannot be empty",
                        provider=self.provider_name,
                        model=self.model_name
                    )
                texts.append(request.text)
            
            # Check batch size limit (OpenAI supports up to 2048 inputs)
            batch_size = 100  # Conservative batch size
            if len(texts) > batch_size:
                # Process in smaller batches
                embeddings = []
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    batch_requests = requests[i:i + batch_size]
                    batch_embeddings = await self._process_batch(batch_texts, batch_requests)
                    embeddings.extend(batch_embeddings)
                return embeddings
            else:
                return await self._process_batch(texts, requests)
                
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate batch embeddings: {str(e)}",
                provider=self.provider_name,
                model=self.model_name,
                cause=e
            )
    
    async def _process_batch(
        self,
        texts: List[str],
        requests: List[EmbeddingRequest]
    ) -> List[np.ndarray]:
        """Process a batch of texts for embedding generation."""
        # Make API request
        response = await self._make_embedding_request(texts)
        
        # Extract embeddings
        embeddings = []
        for i, embedding_data in enumerate(response.data):
            embedding = np.array(embedding_data.embedding, dtype=np.float32)
            
            # Normalize if requested
            if i < len(requests) and requests[i].normalize:
                embedding = self._normalize_embedding(embedding)
            
            embeddings.append(embedding)
        
        logger.debug(f"Generated {len(embeddings)} embeddings in batch")
        return embeddings
    
    async def _make_embedding_request(self, texts: List[str]) -> CreateEmbeddingResponse:
        """Make embedding request to OpenAI API with error handling."""
        try:
            response = await self._client.embeddings.create(
                input=texts,
                model=self.model_name
            )
            return response
            
        except Exception as e:
            error_message = str(e).lower()
            
            # Handle rate limiting
            if "rate limit" in error_message or "429" in error_message:
                raise RateLimitError(
                    f"OpenAI API rate limit exceeded: {str(e)}",
                    provider=self.provider_name,
                    cause=e
                )
            
            # Handle authentication errors
            elif "unauthorized" in error_message or "401" in error_message:
                raise ConfigurationError(
                    f"OpenAI API authentication failed: {str(e)}",
                    config_key="api_key",
                    cause=e
                )
            
            # Handle quota/billing errors
            elif "quota" in error_message or "billing" in error_message:
                raise ConfigurationError(
                    f"OpenAI API quota/billing issue: {str(e)}",
                    cause=e
                )
            
            # Generic API error
            else:
                raise EmbeddingError(
                    f"OpenAI API request failed: {str(e)}",
                    provider=self.provider_name,
                    model=self.model_name,
                    cause=e
                )
    
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding to unit length."""
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm
    
    async def health_check(self) -> bool:
        """
        Check if the OpenAI embedding provider is healthy and accessible.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Try to generate a simple embedding
            test_request = EmbeddingRequest(text="health check")
            await self.generate_embedding(test_request)
            return True
            
        except Exception as e:
            logger.warning(f"OpenAI embedding provider health check failed: {str(e)}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            'provider': self.provider_name,
            'model': self.model_name,
            'dimension': self.embedding_dimension,
            'max_tokens': self.max_tokens,
            'cost_per_1k_tokens': self._model_config['cost_per_1k_tokens']
        }
    
    async def estimate_cost(self, texts: List[str]) -> float:
        """
        Estimate the cost of embedding generation for given texts.
        
        Args:
            texts: List of texts to estimate cost for
            
        Returns:
            Estimated cost in USD
        """
        total_tokens = 0
        for text in texts:
            # Rough token estimation (actual tokenization would be more accurate)
            estimated_tokens = len(text.split()) * 1.3
            total_tokens += estimated_tokens
        
        cost_per_token = self._model_config['cost_per_1k_tokens'] / 1000
        return total_tokens * cost_per_token
