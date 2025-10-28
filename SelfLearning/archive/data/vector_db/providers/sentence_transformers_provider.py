"""
Sentence Transformers embedding provider implementation.

This module provides integration with Sentence Transformers models
for generating vector representations of text content locally.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
import numpy as np

from ..core.interfaces import IEmbeddingProvider
from ..models.vector_models import EmbeddingRequest, EmbeddingModel
from ..utils.exceptions import EmbeddingError, ConfigurationError

logger = logging.getLogger(__name__)


class SentenceTransformersProvider(IEmbeddingProvider):
    """
    Sentence Transformers embedding provider for local embedding generation.
    
    Uses pre-trained sentence transformer models that can run locally
    without requiring API calls to external services.
    """
    
    # Model configurations
    MODEL_CONFIGS = {
        EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MPNET: {
            'name': 'all-MiniLM-L6-v2',
            'dimension': 384,
            'max_tokens': 256,
            'model_size': '80MB'
        },
        EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_DISTILBERT: {
            'name': 'all-distilroberta-v1',
            'dimension': 768,
            'max_tokens': 512,
            'model_size': '290MB'
        }
    }
    
    def __init__(
        self,
        model: EmbeddingModel = EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MPNET,
        device: Optional[str] = None,
        cache_folder: Optional[str] = None
    ):
        """
        Initialize Sentence Transformers embedding provider.
        
        Args:
            model: Embedding model to use
            device: Device to run model on ('cpu', 'cuda', 'mps', etc.)
            cache_folder: Folder to cache downloaded models
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if model not in self.MODEL_CONFIGS:
            raise ConfigurationError(
                f"Unsupported model: {model}",
                config_key="model",
                config_value=str(model)
            )
        
        self._model_enum = model
        self._model_config = self.MODEL_CONFIGS[model]
        self._device = device
        self._cache_folder = cache_folder
        self._model = None
        
        # Initialize model lazily to avoid import errors if sentence-transformers not installed
        self._initialized = False
        
        logger.info(f"Configured Sentence Transformers provider with model {self._model_config['name']}")
    
    async def _initialize_model(self):
        """Initialize the sentence transformer model."""
        if self._initialized:
            return
        
        try:
            # Import sentence-transformers (optional dependency)
            from sentence_transformers import SentenceTransformer
            
            # Load model
            model_name = self._model_config['name']
            self._model = SentenceTransformer(
                model_name,
                device=self._device,
                cache_folder=self._cache_folder
            )
            
            self._initialized = True
            logger.info(f"Initialized Sentence Transformers model: {model_name}")
            
        except ImportError as e:
            raise ConfigurationError(
                "sentence-transformers package not installed. "
                "Install with: pip install sentence-transformers",
                cause=e
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize Sentence Transformers model: {str(e)}",
                cause=e
            )
    
    @property
    def provider_name(self) -> str:
        """Get the name of the embedding provider."""
        return "sentence_transformers"
    
    @property
    def model_name(self) -> str:
        """Get the name of the embedding model."""
        return self._model_config['name']
    
    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        return self._model_config['dimension']
    
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
            # Initialize model if needed
            await self._initialize_model()
            
            # Validate input
            if not request.text.strip():
                raise EmbeddingError(
                    "Input text cannot be empty",
                    provider=self.provider_name,
                    model=self.model_name
                )
            
            # Generate embedding
            embedding = await self._generate_embedding_sync(request.text)
            
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
            # Initialize model if needed
            await self._initialize_model()
            
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
            
            # Generate embeddings in batch
            embeddings = await self._generate_embeddings_batch_sync(texts)
            
            # Apply normalization if requested
            normalized_embeddings = []
            for i, embedding in enumerate(embeddings):
                if i < len(requests) and requests[i].normalize:
                    embedding = self._normalize_embedding(embedding)
                normalized_embeddings.append(embedding)
            
            logger.debug(f"Generated {len(normalized_embeddings)} embeddings in batch")
            return normalized_embeddings
            
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate batch embeddings: {str(e)}",
                provider=self.provider_name,
                model=self.model_name,
                cause=e
            )
    
    async def _generate_embedding_sync(self, text: str) -> np.ndarray:
        """Generate embedding synchronously (wrapped in async)."""
        loop = asyncio.get_event_loop()
        
        def _encode():
            return self._model.encode([text], convert_to_numpy=True)[0]
        
        embedding = await loop.run_in_executor(None, _encode)
        return embedding.astype(np.float32)
    
    async def _generate_embeddings_batch_sync(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for batch synchronously (wrapped in async)."""
        loop = asyncio.get_event_loop()
        
        def _encode_batch():
            return self._model.encode(texts, convert_to_numpy=True)
        
        embeddings = await loop.run_in_executor(None, _encode_batch)
        return [emb.astype(np.float32) for emb in embeddings]
    
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding to unit length."""
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm
    
    async def health_check(self) -> bool:
        """
        Check if the Sentence Transformers provider is healthy and accessible.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Try to initialize and generate a simple embedding
            await self._initialize_model()
            test_request = EmbeddingRequest(text="health check")
            await self.generate_embedding(test_request)
            return True
            
        except Exception as e:
            logger.warning(f"Sentence Transformers provider health check failed: {str(e)}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            'provider': self.provider_name,
            'model': self.model_name,
            'dimension': self.embedding_dimension,
            'max_tokens': self._model_config['max_tokens'],
            'model_size': self._model_config['model_size'],
            'device': self._device or 'auto',
            'local': True,
            'requires_internet': False
        }
    
    async def estimate_cost(self, texts: List[str]) -> float:
        """
        Estimate the cost of embedding generation for given texts.
        
        Since this is a local model, the cost is always 0.
        
        Args:
            texts: List of texts to estimate cost for
            
        Returns:
            Cost (always 0.0 for local models)
        """
        return 0.0
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported model names."""
        return [config['name'] for config in self.MODEL_CONFIGS.values()]
    
    async def download_model(self) -> bool:
        """
        Download and cache the model if not already available.
        
        Returns:
            True if model is available, False otherwise
        """
        try:
            await self._initialize_model()
            return True
        except Exception as e:
            logger.error(f"Failed to download model: {str(e)}")
            return False
