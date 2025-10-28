"""
Health Check API Router.

Provides health check endpoints for monitoring and orchestration.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ...core.crawler import WebCrawler

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Current timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")


def get_crawler_dep() -> WebCrawler:
    """Dependency to get crawler instance."""
    from ..main import get_crawler
    return get_crawler()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=200,
    summary="Health check",
    description="Check if the service is healthy and operational."
)
async def health_check(
    crawler: WebCrawler = Depends(get_crawler_dep)
) -> HealthResponse:
    """
    Health check endpoint for monitoring.
    
    Returns service health status and basic diagnostics.
    """
    try:
        # Check crawler status
        crawler_healthy = crawler is not None
        session_active = crawler._session is not None if crawler else False
        
        # Check output directory
        output_dir_exists = crawler.config.output_directory.exists() if crawler else False
        
        # Determine overall health
        is_healthy = crawler_healthy and output_dir_exists
        
        return HealthResponse(
            status="healthy" if is_healthy else "degraded",
            service="web-crawler-service",
            timestamp=datetime.utcnow().isoformat() + "Z",
            details={
                "crawler_initialized": crawler_healthy,
                "session_active": session_active,
                "output_directory_exists": output_dir_exists,
                "output_directory": str(crawler.config.output_directory) if crawler else None
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "web-crawler-service",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }
        )


@router.get(
    "/ready",
    status_code=200,
    summary="Readiness check",
    description="Check if the service is ready to accept requests."
)
async def readiness_check(
    crawler: WebCrawler = Depends(get_crawler_dep)
):
    """
    Readiness check for Kubernetes/orchestration.
    
    Returns 200 if service is ready, 503 otherwise.
    """
    try:
        if crawler is None:
            return JSONResponse(
                status_code=503,
                content={"ready": False, "reason": "Crawler not initialized"}
            )
        
        if not crawler.config.output_directory.exists():
            return JSONResponse(
                status_code=503,
                content={"ready": False, "reason": "Output directory not accessible"}
            )
        
        return {"ready": True, "service": "web-crawler-service"}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": str(e)}
        )


@router.get(
    "/live",
    status_code=200,
    summary="Liveness check",
    description="Check if the service is alive (for Kubernetes liveness probe)."
)
async def liveness_check():
    """
    Liveness check for Kubernetes/orchestration.
    
    Simple check to verify the service process is running.
    """
    return {"alive": True, "service": "web-crawler-service"}

