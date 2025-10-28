"""
Text generation endpoints for LLM Service.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ...core.service import LLMService
from ...core.interfaces import LLMProvider
from ..dependencies import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/generate",
    tags=["Generation"],
)


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request for text generation."""
    prompt: str = Field(..., description="Input prompt for generation", min_length=1)
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate", ge=1, le=4000)
    temperature: Optional[float] = Field(0.7, description="Sampling temperature", ge=0.0, le=2.0)
    provider: Optional[str] = Field("openai", description="LLM provider (openai/anthropic)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Explain quantum computing in simple terms",
                "max_tokens": 200,
                "temperature": 0.7,
                "provider": "openai"
            }
        }


class GenerateResponse(BaseModel):
    """Response from text generation."""
    content: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used for generation")
    provider: str = Field(..., description="Provider used")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Quantum computing uses quantum bits...",
                "model": "gpt-4",
                "provider": "openai",
                "tokens_used": 150
            }
        }


@router.post(
    "",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate text",
    description="Generate text using LLM based on a prompt."
)
async def generate_text(
    request: GenerateRequest,
    llm_service: LLMService = Depends(get_llm_service)
) -> GenerateResponse:
    """Generate text using LLM."""
    try:
        # Map provider string to enum
        provider_map = {
            "openai": LLMProvider.OPENAI,
            "anthropic": LLMProvider.ANTHROPIC
        }
        provider = provider_map.get(request.provider.lower(), LLMProvider.OPENAI)
        
        # Generate
        response = await llm_service.generate(
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            provider=provider
        )
        
        return GenerateResponse(
            content=response.content,
            model=response.model,
            provider=response.provider if isinstance(response.provider, str) else response.provider.value,
            tokens_used=getattr(response, 'tokens_used', None)
        )
    
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )

