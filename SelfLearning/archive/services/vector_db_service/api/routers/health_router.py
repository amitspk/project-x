"""
Health Check Router for Vector DB Service.
"""

import logging
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any

from ...data.database import db_manager
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    service: str
    status: str
    timestamp: str
    database: Dict[str, Any]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check service and database health status."
)
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        db_health = await db_manager.health_check()
        is_healthy = db_health.get('status') == 'healthy'
        
        response = HealthResponse(
            service=settings.service_name,
            status="healthy" if is_healthy else "degraded",
            timestamp=datetime.utcnow().isoformat() + "Z",
            database=db_health
        )
        
        status_code = 200 if is_healthy else 503
        return JSONResponse(
            status_code=status_code,
            content=response.dict()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "service": settings.service_name,
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }
        )


@router.get("/ready", summary="Readiness check")
async def readiness_check():
    """Readiness check for Kubernetes."""
    if not db_manager.is_connected:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "Database not connected"}
        )
    return {"ready": True, "service": settings.service_name}


@router.get("/live", summary="Liveness check")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"alive": True, "service": settings.service_name}

