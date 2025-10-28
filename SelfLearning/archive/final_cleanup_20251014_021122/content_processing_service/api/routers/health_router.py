"""Health check router."""

import logging
from datetime import datetime
from fastapi import APIRouter, Request
from ...models.schemas import HealthCheckResponse
from ...data.database import db_manager
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request):
    """Health check endpoint."""
    
    # Check database
    db_health = await db_manager.health_check()
    
    # Check LLM (basic check - just verify API key is set)
    llm_health = {
        "status": "configured" if settings.openai_api_key else "not_configured",
        "model": settings.llm_model
    }
    
    # Overall status
    overall_status = "healthy" if db_health.get("status") == "healthy" and llm_health["status"] == "configured" else "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.utcnow(),
        database=db_health,
        llm=llm_health
    )

