"""
Health check router for the blog manager microservice.

Provides endpoints for monitoring service health and status.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...core.config import settings
from ...data.database import db_manager
from ...models.response_models import HealthResponse
from ...core.resilience import get_circuit_breakers

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health", 
    response_model=HealthResponse,
    summary="Service health check",
    description="Get comprehensive health status of the service and its dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2025-10-02T20:52:42.869Z",
                        "version": "1.0.0",
                        "database_status": "connected",
                        "uptime_seconds": 3600.5,
                        "details": {
                            "database": {
                                "status": "healthy",
                                "ping_time_ms": 2.5,
                                "collections_count": 4,
                                "data_size_mb": 15.2
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "timestamp": "2025-10-02T20:52:42.869Z",
                        "version": "1.0.0",
                        "database_status": "error",
                        "details": {
                            "error": "Database connection failed"
                        }
                    }
                }
            }
        }
    },
    tags=["Health"]
)
async def health_check():
    """
    Health check endpoint.
    
    Returns the current health status of the service and its dependencies.
    """
    try:
        # Get database health
        db_health = await db_manager.health_check()
        
        # Determine overall status
        overall_status = "healthy" if db_health['status'] == 'healthy' else "unhealthy"
        database_status = db_health['status']
        
        # Get uptime
        uptime_seconds = db_health.get('uptime_seconds')
        
        # Get circuit breaker status
        circuit_breakers = get_circuit_breakers()
        breaker_status = circuit_breakers.get_breaker_status()
        
        # Count open/closed breakers
        all_closed = all(b['state'] == 'closed' for b in breaker_status.values())
        open_breakers = [name for name, status in breaker_status.items() if status['state'] == 'open']
        
        # Prepare detailed health information
        details = {
            "database": {
                "status": database_status,
                "ping_time_ms": db_health.get('ping_time_ms'),
                "collections_count": db_health.get('collections_count', 0),
                "data_size_mb": db_health.get('data_size_mb', 0)
            },
            "service": {
                "name": settings.app_name,
                "debug_mode": settings.debug,
                "api_prefix": settings.api_prefix
            },
            "circuit_breakers": {
                "all_closed": all_closed,
                "open_breakers": open_breakers,
                "details": breaker_status
            }
        }
        
        # Add database stats if available
        if db_manager.is_connected:
            try:
                db_stats = await db_manager.get_database_stats()
                details["database"]["stats"] = db_stats
            except Exception as e:
                logger.warning(f"Failed to get database stats: {e}")
                details["database"]["stats_error"] = str(e)
        
        response = HealthResponse(
            status=overall_status,
            version=settings.app_version,
            database_status=database_status,
            uptime_seconds=uptime_seconds,
            details=details
        )
        
        # Return appropriate HTTP status
        status_code = 200 if overall_status == "healthy" else 503
        
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump(mode='json')
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        error_response = HealthResponse(
            status="unhealthy",
            version=settings.app_version,
            database_status="error",
            details={"error": str(e)}
        )
        
        return JSONResponse(
            status_code=503,
            content=error_response.model_dump(mode='json')
        )


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Check if the service is ready to accept requests",
    responses={
        200: {
            "description": "Service is ready",
            "content": {
                "application/json": {
                    "example": {
                        "ready": True,
                        "timestamp": "2025-10-02T20:52:42.869Z",
                        "database_status": "healthy"
                    }
                }
            }
        },
        503: {
            "description": "Service is not ready",
            "content": {
                "application/json": {
                    "example": {
                        "ready": False,
                        "reason": "Database not connected",
                        "timestamp": "2025-10-02T20:52:42.869Z"
                    }
                }
            }
        }
    },
    tags=["Health"]
)
async def readiness_check():
    """
    Readiness check endpoint.
    
    Returns whether the service is ready to accept requests.
    """
    try:
        # Check if database is connected and healthy
        if not db_manager.is_connected:
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "reason": "Database not connected",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Perform a quick database ping
        db_health = await db_manager.health_check()
        if db_health['status'] != 'healthy':
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "reason": f"Database unhealthy: {db_health.get('error', 'Unknown error')}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat(),
            "database_status": "healthy"
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "reason": f"Readiness check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get(
    "/health/live",
    summary="Liveness check",
    description="Check if the service is alive and running",
    responses={
        200: {
            "description": "Service is alive",
            "content": {
                "application/json": {
                    "example": {
                        "alive": True,
                        "timestamp": "2025-10-02T20:52:42.869Z",
                        "service": "Blog Manager Microservice",
                        "version": "1.0.0"
                    }
                }
            }
        }
    },
    tags=["Health"]
)
async def liveness_check():
    """
    Liveness check endpoint.
    
    Returns whether the service is alive and running.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.app_version
    }
