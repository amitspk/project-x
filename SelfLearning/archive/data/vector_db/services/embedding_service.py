"""
Embedding service for managing multiple embedding providers.

This module provides a unified interface for generating embeddings
using different providers with fallback and load balancing capabilities.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np
from datetime import datetime

from ..core.interfaces import IEmbeddingProvider
from ..models.vector_models import EmbeddingRequest, EmbeddingModel
from ..providers.openai_provider import OpenAIEmbeddingProvider
from ..providers.anthropic_provider import AnthropicEmbeddingProvider
from ..providers.sentence_transformers_provider import SentenceTransformersProvider
from ..utils.exceptions import EmbeddingError, ConfigurationError, RateLimitError
from ..utils.text_processing import TextPreprocessor, TextChunker, ChunkingConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for managing embedding generation with multiple providers.
    
    Provides a unified interface for embedding generation with features like:
    - Multiple provider support with fallback
    - Text preprocessing and chunking
    - Batch processing optimization
    - Error handling and retry logic
    - Provider health monitoring
    """
    
    def __init__(
        self,
        primary_provider: Optional[IEmbeddingProvider] = None,
        fallback_providers: Optional[List[IEmbeddingProvider]] = None,
        enable_preprocessing: bool = True,
        enable_chunking: bool = True,
        chunking_config: Optional[ChunkingConfig] = None
    ):
        """
        Initialize embedding service.
        
        Args:
            primary_provider: Primary embedding provider
            fallback_providers: List of fallback providers
            enable_preprocessing: Whether to enable text preprocessing
            enable_chunking: Whether to enable text chunking for long texts
            chunking_config: Configuration for text chunking
        """
        self._primary_provider = primary_provider
        self._fallback_providers = fallback_providers or []
        self._all_providers = [primary_provider] + self._fallback_providers if primary_provider else []
        
        # Text processing components
        self._preprocessor = TextPreprocessor() if enable_preprocessing else None
        self._chunker = TextChunker(chunking_config) if enable_chunking else None
        
        # Service state
        self._provider_health: Dict[str, bool] = {}
        self._provider_stats: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Initialized embedding service with {len(self._all_providers)} providers")
    
    def add_provider(self, provider: IEmbeddingProvider, is_primary: bool = False) -> None:
        """
        Add an embedding provider to the service.
        
        Args:
            provider: Embedding provider to add
            is_primary: Whether this should be the primary provider
        """
        if is_primary:
            if self._primary_provider:
                self._fallback_providers.insert(0, self._primary_provider)
            self._primary_provider = provider
            self._all_providers = [provider] + self._fallback_providers
        else:
            self._fallback_providers.append(provider)
            if provider not in self._all_providers:
                self._all_providers.append(provider)
        
        logger.info(f"Added provider {provider.provider_name} ({'primary' if is_primary else 'fallback'})")
    
    def remove_provider(self, provider_name: str) -> bool:
        """
        Remove a provider by name.
        
        Args:
            provider_name: Name of provider to remove
            
        Returns:
            True if provider was removed, False if not found
        """
        removed = False
        
        # Remove from primary
        if self._primary_provider and self._primary_provider.provider_name == provider_name:
            self._primary_provider = None
            removed = True
        
        # Remove from fallbacks
        self._fallback_providers = [
            p for p in self._fallback_providers 
            if p.provider_name != provider_name
        ]
        
        # Rebuild all providers list
        self._all_providers = (
            [self._primary_provider] if self._primary_provider else []
        ) + self._fallback_providers
        
        if removed:
            logger.info(f"Removed provider {provider_name}")
        
        return removed
    
    async def generate_embedding(
        self,
        text: str,
        model: Optional[EmbeddingModel] = None,
        preprocess: bool = True,
        normalize: bool = True,
        chunk_if_needed: bool = True
    ) -> np.ndarray:
        """
        Generate embedding for a single text input.
        
        Args:
            text: Text to generate embedding for
            model: Specific model to use (optional)
            preprocess: Whether to preprocess the text
            normalize: Whether to normalize the embedding
            chunk_if_needed: Whether to chunk long texts and average embeddings
            
        Returns:
            Numpy array containing the embedding vector
            
        Raises:
            EmbeddingError: If embedding generation fails with all providers
        """
        try:
            # Preprocess text if enabled
            processed_text = text
            if preprocess and self._preprocessor:
                processed_text = self._preprocessor.preprocess(text)
            
            # Handle long texts with chunking
            if chunk_if_needed and self._chunker:
                chunks = self._chunker.chunk_text(processed_text)
                if len(chunks) > 1:
                    return await self._generate_embedding_from_chunks(
                        chunks, model, normalize
                    )
            
            # Create embedding request
            request = EmbeddingRequest(
                text=processed_text,
                model=model,
                normalize=normalize
            )
            
            # Try providers in order
            last_error = None
            for provider in self._all_providers:
                try:
                    # Skip unhealthy providers
                    if not await self._is_provider_healthy(provider):
                        continue
                    
                    # Skip if model doesn't match (if specified)
                    if model and hasattr(provider, '_model') and provider._model != model:
                        continue
                    
                    embedding = await provider.generate_embedding(request)
                    
                    # Update provider stats
                    self._update_provider_stats(provider.provider_name, success=True)
                    
                    logger.debug(f"Generated embedding using {provider.provider_name}")
                    return embedding
                    
                except RateLimitError as e:
                    logger.warning(f"Rate limit hit for {provider.provider_name}: {str(e)}")
                    last_error = e
                    continue
                    
                except Exception as e:
                    logger.warning(f"Provider {provider.provider_name} failed: {str(e)}")
                    self._update_provider_stats(provider.provider_name, success=False)
                    last_error = e
                    continue
            
            # All providers failed
            raise EmbeddingError(
                f"All embedding providers failed. Last error: {str(last_error)}",
                cause=last_error
            )
            
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate embedding: {str(e)}",
                cause=e
            )
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
        preprocess: bool = True,
        normalize: bool = True,
        batch_size: int = 100
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to generate embeddings for
            model: Specific model to use (optional)
            preprocess: Whether to preprocess the texts
            normalize: Whether to normalize the embeddings
            batch_size: Maximum batch size for processing
            
        Returns:
            List of numpy arrays containing embedding vectors
            
        Raises:
            EmbeddingError: If batch embedding generation fails
        """
        if not texts:
            return []
        
        try:
            # Preprocess texts if enabled
            processed_texts = texts
            if preprocess and self._preprocessor:
                processed_texts = [
                    self._preprocessor.preprocess(text) for text in texts
                ]
            
            # Create embedding requests
            requests = [
                EmbeddingRequest(text=text, model=model, normalize=normalize)
                for text in processed_texts
            ]
            
            # Process in batches
            all_embeddings = []
            for i in range(0, len(requests), batch_size):
                batch_requests = requests[i:i + batch_size]
                batch_embeddings = await self._process_batch_with_fallback(batch_requests)
                all_embeddings.extend(batch_embeddings)
            
            logger.debug(f"Generated {len(all_embeddings)} embeddings in batch")
            return all_embeddings
            
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate batch embeddings: {str(e)}",
                cause=e
            )
    
    async def _generate_embedding_from_chunks(
        self,
        chunks: List[str],
        model: Optional[EmbeddingModel],
        normalize: bool
    ) -> np.ndarray:
        """Generate embedding by averaging embeddings from text chunks."""
        chunk_embeddings = []
        
        for chunk in chunks:
            request = EmbeddingRequest(text=chunk, model=model, normalize=False)
            
            # Try providers for this chunk
            for provider in self._all_providers:
                try:
                    if not await self._is_provider_healthy(provider):
                        continue
                    
                    embedding = await provider.generate_embedding(request)
                    chunk_embeddings.append(embedding)
                    break
                    
                except Exception as e:
                    logger.warning(f"Chunk embedding failed with {provider.provider_name}: {str(e)}")
                    continue
            else:
                raise EmbeddingError(f"Failed to generate embedding for chunk: {chunk[:100]}...")
        
        if not chunk_embeddings:
            raise EmbeddingError("Failed to generate embeddings for any chunks")
        
        # Average the chunk embeddings
        averaged_embedding = np.mean(chunk_embeddings, axis=0)
        
        # Normalize if requested
        if normalize:
            norm = np.linalg.norm(averaged_embedding)
            if norm > 0:
                averaged_embedding = averaged_embedding / norm
        
        return averaged_embedding
    
    async def _process_batch_with_fallback(
        self,
        requests: List[EmbeddingRequest]
    ) -> List[np.ndarray]:
        """Process a batch of requests with provider fallback."""
        last_error = None
        
        for provider in self._all_providers:
            try:
                if not await self._is_provider_healthy(provider):
                    continue
                
                embeddings = await provider.generate_embeddings_batch(requests)
                
                # Update provider stats
                self._update_provider_stats(provider.provider_name, success=True)
                
                return embeddings
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit for {provider.provider_name}: {str(e)}")
                last_error = e
                continue
                
            except Exception as e:
                logger.warning(f"Batch processing failed with {provider.provider_name}: {str(e)}")
                self._update_provider_stats(provider.provider_name, success=False)
                last_error = e
                continue
        
        # All providers failed
        raise EmbeddingError(
            f"All providers failed for batch processing. Last error: {str(last_error)}",
            cause=last_error
        )
    
    async def _is_provider_healthy(self, provider: IEmbeddingProvider) -> bool:
        """Check if a provider is healthy (with caching)."""
        provider_name = provider.provider_name
        
        # Check cached health status (cache for 5 minutes)
        if provider_name in self._provider_health:
            return self._provider_health[provider_name]
        
        # Perform health check
        try:
            is_healthy = await provider.health_check()
            self._provider_health[provider_name] = is_healthy
            
            # Clear cache after 5 minutes
            asyncio.create_task(self._clear_health_cache(provider_name, 300))
            
            return is_healthy
            
        except Exception as e:
            logger.warning(f"Health check failed for {provider_name}: {str(e)}")
            self._provider_health[provider_name] = False
            return False
    
    async def _clear_health_cache(self, provider_name: str, delay: int):
        """Clear health cache after delay."""
        await asyncio.sleep(delay)
        self._provider_health.pop(provider_name, None)
    
    def _update_provider_stats(self, provider_name: str, success: bool):
        """Update provider statistics."""
        if provider_name not in self._provider_stats:
            self._provider_stats[provider_name] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'last_used': None
            }
        
        stats = self._provider_stats[provider_name]
        stats['total_requests'] += 1
        stats['last_used'] = datetime.now()
        
        if success:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1
    
    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all providers."""
        return self._provider_stats.copy()
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [provider.provider_name for provider in self._all_providers]
    
    def get_primary_provider(self) -> Optional[IEmbeddingProvider]:
        """Get the primary provider."""
        return self._primary_provider
    
    async def health_check_all_providers(self) -> Dict[str, bool]:
        """Perform health check on all providers."""
        results = {}
        
        for provider in self._all_providers:
            try:
                is_healthy = await provider.health_check()
                results[provider.provider_name] = is_healthy
            except Exception as e:
                logger.warning(f"Health check failed for {provider.provider_name}: {str(e)}")
                results[provider.provider_name] = False
        
        return results
    
    @classmethod
    def create_default_service(
        cls,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        use_sentence_transformers: bool = True
    ) -> 'EmbeddingService':
        """
        Create a default embedding service with common providers.
        
        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            use_sentence_transformers: Whether to include sentence transformers
            
        Returns:
            Configured embedding service
        """
        providers = []
        
        # Add OpenAI provider if API key is provided
        if openai_api_key:
            try:
                openai_provider = OpenAIEmbeddingProvider(api_key=openai_api_key)
                providers.append(openai_provider)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {str(e)}")
        
        # Add Anthropic provider if API key is provided
        if anthropic_api_key:
            try:
                anthropic_provider = AnthropicEmbeddingProvider(api_key=anthropic_api_key)
                providers.append(anthropic_provider)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {str(e)}")
        
        # Add Sentence Transformers provider (local, no API key needed)
        if use_sentence_transformers:
            try:
                st_provider = SentenceTransformersProvider()
                providers.append(st_provider)
            except Exception as e:
                logger.warning(f"Failed to initialize Sentence Transformers provider: {str(e)}")
        
        if not providers:
            raise ConfigurationError("No embedding providers could be initialized")
        
        # Use first provider as primary, rest as fallbacks
        primary = providers[0]
        fallbacks = providers[1:] if len(providers) > 1 else []
        
        return cls(primary_provider=primary, fallback_providers=fallbacks)
