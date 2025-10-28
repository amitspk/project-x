"""
Embeddings generation endpoints for LLM Service.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ...core.service import LLMService
from ..dependencies import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/embeddings",
    tags=["Embeddings"],
)


# Request/Response Models
class EmbeddingRequest(BaseModel):
    """Request for embedding generation."""
    text: str = Field(..., description="Text to generate embedding for", min_length=1)
    model: str = Field("text-embedding-ada-002", description="Embedding model to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Python is a programming language",
                "model": "text-embedding-ada-002"
            }
        }


class BatchEmbeddingRequest(BaseModel):
    """Request for batch embedding generation."""
    texts: List[str] = Field(..., description="Texts to generate embeddings for", min_items=1, max_items=100)
    model: str = Field("text-embedding-ada-002", description="Embedding model to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "texts": [
                    "Python is a programming language",
                    "JavaScript is used for web development"
                ],
                "model": "text-embedding-ada-002"
            }
        }


class EmbeddingResponse(BaseModel):
    """Response from embedding generation."""
    embedding: List[float] = Field(..., description="Generated embedding vector")
    model: str = Field(..., description="Model used")
    dimensions: int = Field(..., description="Embedding dimensions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "embedding": [0.123, -0.456, 0.789],
                "model": "text-embedding-ada-002",
                "dimensions": 1536
            }
        }


class BatchEmbeddingResponse(BaseModel):
    """Response from batch embedding generation."""
    embeddings: List[List[float]] = Field(..., description="Generated embedding vectors")
    model: str = Field(..., description="Model used")
    dimensions: int = Field(..., description="Embedding dimensions")
    total_texts: int = Field(..., description="Number of texts processed")


@router.post(
    "/generate",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate embedding",
    description="Generate vector embedding for a single text."
)
async def generate_embedding(
    request: EmbeddingRequest,
    llm_service: LLMService = Depends(get_llm_service)
) -> EmbeddingResponse:
    """Generate embedding for a single text."""
    try:
        # Use OpenAI directly for embeddings
        import openai
        from openai import AsyncOpenAI
        from ...config.settings import LLMServiceConfig
        
        settings = LLMServiceConfig()
        api_key = settings.openai.api_key
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key not configured"
            )
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Generate embedding
        response = await client.embeddings.create(
            input=request.text,
            model=request.model
        )
        
        embedding = response.data[0].embedding
        
        return EmbeddingResponse(
            embedding=embedding,
            model=request.model,
            dimensions=len(embedding)
        )
    
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {str(e)}"
        )


@router.post(
    "/generate-batch",
    response_model=BatchEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate embeddings (batch)",
    description="Generate vector embeddings for multiple texts in batch."
)
async def generate_embeddings_batch(
    request: BatchEmbeddingRequest,
    llm_service: LLMService = Depends(get_llm_service)
) -> BatchEmbeddingResponse:
    """Generate embeddings for multiple texts in batch."""
    try:
        # Use OpenAI directly for embeddings
        import openai
        from openai import AsyncOpenAI
        from ...config.settings import LLMServiceConfig
        
        settings = LLMServiceConfig()
        api_key = settings.openai.api_key
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key not configured"
            )
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Generate embeddings - OpenAI supports batch input
        response = await client.embeddings.create(
            input=request.texts,
            model=request.model
        )
        
        embeddings = [item.embedding for item in response.data]
        dimensions = len(embeddings[0]) if embeddings else 0
        
        return BatchEmbeddingResponse(
            embeddings=embeddings,
            model=request.model,
            dimensions=dimensions,
            total_texts=len(embeddings)
        )
    
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch embedding generation failed: {str(e)}"
        )

