"""
Prometheus metrics middleware for FastAPI.

Tracks HTTP requests, response times, and errors automatically.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from fyi_widget_api.api.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_active,
    normalize_endpoint,
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track HTTP metrics for Prometheus.
    
    Tracks:
    - Request count by method, endpoint, status code
    - Request duration (histogram for percentiles)
    - Active requests (gauge)
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Exclude metrics endpoint and health checks from detailed tracking
        self.excluded_paths = ['/metrics', '/health', '/docs', '/openapi.json', '/redoc', '/']
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process each request and track metrics."""
        # Normalize endpoint path
        endpoint = normalize_endpoint(request.url.path)
        method = request.method
        
        # Get route tag if available
        route_tag = 'unknown'
        if hasattr(request.scope, 'route') and request.scope.get('route'):
            route = request.scope['route']
            # Try to get the route tag from the router
            if hasattr(route, 'tags') and route.tags:
                route_tag = route.tags[0] if route.tags else 'unknown'
        
        # Skip detailed tracking for excluded paths (but still count them)
        is_excluded = endpoint in self.excluded_paths
        
        # Start tracking active request
        if not is_excluded:
            http_requests_active.labels(method=method, endpoint=endpoint).inc()
        
        # Start timer
        start_time = time.time()
        status_code = 500  # Default to error status
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics (count each request exactly once)
            if is_excluded:
                # Excluded paths: track with simplified labels
                http_requests_total.labels(
                    method=method,
                    endpoint='excluded',
                    status_code=status_code,
                    route_tag='system'
                ).inc()
            else:
                # Non-excluded paths: track with detailed labels
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    route_tag=route_tag
                ).inc()
                
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    route_tag=route_tag
                ).observe(duration)
            
            return response
            
        except Exception:
            # Calculate duration even on error
            duration = time.time() - start_time
            
            # Record error metrics
            status_code = 500
            if not is_excluded:
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    route_tag=route_tag
                ).inc()
                
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    route_tag=route_tag
                ).observe(duration)
            
            # Re-raise exception
            raise
            
        finally:
            # Decrement active requests
            if not is_excluded:
                http_requests_active.labels(method=method, endpoint=endpoint).dec()

__all__ = ["MetricsMiddleware"]

