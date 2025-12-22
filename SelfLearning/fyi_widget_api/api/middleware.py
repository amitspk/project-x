"""
Middleware for API service.

Includes request ID generation, logging, and response handling.
"""

import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from fyi_widget_shared_library.utils import generate_request_id

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically generate and attach request IDs to all incoming requests.
    
    Features:
    - Generates a unique request ID for each request
    - Stores it in request.state.request_id for endpoint access
    - Adds X-Request-ID header to responses
    - Logs request details with request ID
    - Tracks request duration
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request.
        
        Args:
            request: The incoming request
            call_next: The next middleware/endpoint handler
            
        Returns:
            Response with added X-Request-ID header
        """
        # Generate request ID
        request_id = generate_request_id()
        
        # Store in request state for endpoint access
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"- Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Capture raw body for PUT/PATCH requests to publisher endpoints
        # This is needed because FastAPI/Pydantic consumes the request body,
        # making it unavailable for subsequent reads without special handling
        if request.method in ["PUT", "PATCH"] and request.url.path.startswith("/api/v1/publishers/"):
            try:
                body = await request.body()
                raw_body_str = body.decode('utf-8')
                request.state.raw_body = raw_body_str
                logger.info(f"[{request_id}] 📦 Captured raw body ({len(raw_body_str)} bytes) for {request.method} {request.url.path}")
                
                # Recreate the request body stream so FastAPI/Pydantic can still process it
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except Exception as e:
                logger.warning(f"[{request_id}] ⚠️ Failed to capture raw body: {e}", exc_info=True)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log response
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Duration: {duration:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # Calculate duration even on error
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- Error: {str(e)} - Duration: {duration:.3f}s",
                exc_info=True
            )
            
            # Re-raise to let FastAPI's exception handlers deal with it
            raise


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log detailed request information.
    
    Optional, more verbose logging middleware that can be enabled
    for debugging or monitoring purposes.
    """
    
    def __init__(self, app: ASGIApp, log_body: bool = False):
        super().__init__(app)
        self.log_body = log_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process each request with detailed logging."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Log request details
        logger.debug(
            f"[{request_id}] Request Headers: {dict(request.headers)}"
        )
        
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                logger.debug(f"[{request_id}] Request Body: {body.decode()}")
            except Exception as e:
                logger.debug(f"[{request_id}] Could not log request body: {e}")
        
        response = await call_next(request)
        
        # Log response headers
        logger.debug(
            f"[{request_id}] Response Headers: {dict(response.headers)}"
        )
        
        return response

