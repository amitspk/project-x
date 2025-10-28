"""
Utility functions for generating standardized API responses.

Provides helper functions to create consistent responses across all endpoints.
"""

import uuid
import logging
from typing import Any, Optional, List, Dict
from datetime import datetime
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from shared.models.api_response import (
    StandardResponse,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    ResponseMetadata
)

logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


def success_response(
    result: Any,
    message: str = "Operation completed successfully",
    status_code: int = 200,
    metadata: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        result: The response data
        message: Human-readable success message
        status_code: HTTP status code (default: 200)
        metadata: Optional metadata (pagination, counts, etc.)
        warnings: Optional list of non-fatal warnings
        request_id: Optional request ID (generated if not provided)
        
    Returns:
        Dictionary containing standardized success response
        
    Example:
        >>> success_response(
        ...     result={"questions": [...]},
        ...     message="Questions retrieved successfully",
        ...     metadata={"total": 10}
        ... )
    """
    if request_id is None:
        request_id = generate_request_id()
    
    response_metadata = ResponseMetadata(**metadata) if metadata else None
    
    response = SuccessResponse(
        status="success",
        status_code=status_code,
        message=message,
        result=result,
        metadata=response_metadata,
        warnings=warnings,
        request_id=request_id,
        timestamp=datetime.utcnow()
    )
    
    # Convert to dict and ensure datetime is serialized
    response_dict = response.model_dump(exclude_none=True)
    if 'timestamp' in response_dict and isinstance(response_dict['timestamp'], datetime):
        response_dict['timestamp'] = response_dict['timestamp'].isoformat()
    
    return response_dict


def error_response(
    message: str,
    error_code: str,
    detail: str,
    status_code: int = 400,
    field: Optional[str] = None,
    warnings: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        message: Human-readable error message
        error_code: Machine-readable error code (e.g., "NOT_FOUND", "VALIDATION_ERROR")
        detail: Detailed error description
        status_code: HTTP status code (default: 400)
        field: Optional field name for validation errors
        warnings: Optional list of warnings
        request_id: Optional request ID (generated if not provided)
        
    Returns:
        Dictionary containing standardized error response
        
    Example:
        >>> error_response(
        ...     message="Resource not found",
        ...     error_code="NOT_FOUND",
        ...     detail="No questions found for the specified URL",
        ...     status_code=404,
        ...     field="blog_url"
        ... )
    """
    if request_id is None:
        request_id = generate_request_id()
    
    error_detail = ErrorDetail(
        code=error_code,
        detail=detail,
        field=field
    )
    
    response = ErrorResponse(
        status="error",
        status_code=status_code,
        message=message,
        error=error_detail,
        warnings=warnings,
        request_id=request_id,
        timestamp=datetime.utcnow()
    )
    
    # Convert to dict and ensure datetime is serialized
    response_dict = response.model_dump(exclude_none=True)
    if 'timestamp' in response_dict and isinstance(response_dict['timestamp'], datetime):
        response_dict['timestamp'] = response_dict['timestamp'].isoformat()
    
    return response_dict


def create_json_response(
    data: Dict[str, Any],
    status_code: int = 200
) -> JSONResponse:
    """
    Create a FastAPI JSONResponse with standardized format.
    
    Args:
        data: Response data (from success_response or error_response)
        status_code: HTTP status code
        
    Returns:
        FastAPI JSONResponse object
    """
    return JSONResponse(
        content=data,
        status_code=status_code
    )


def success_json_response(
    result: Any,
    message: str = "Operation completed successfully",
    status_code: int = 200,
    **kwargs
) -> JSONResponse:
    """
    Create a success JSONResponse directly.
    
    Convenience function combining success_response and create_json_response.
    """
    response_data = success_response(
        result=result,
        message=message,
        status_code=status_code,
        **kwargs
    )
    return create_json_response(response_data, status_code)


def error_json_response(
    message: str,
    error_code: str,
    detail: str,
    status_code: int = 400,
    **kwargs
) -> JSONResponse:
    """
    Create an error JSONResponse directly.
    
    Convenience function combining error_response and create_json_response.
    """
    response_data = error_response(
        message=message,
        error_code=error_code,
        detail=detail,
        status_code=status_code,
        **kwargs
    )
    return create_json_response(response_data, status_code)


def handle_http_exception(
    exc: HTTPException,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert HTTPException to standardized error response.
    
    Args:
        exc: FastAPI HTTPException
        request_id: Optional request ID
        
    Returns:
        Standardized error response dictionary
    """
    # Map HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    
    error_code = error_code_map.get(exc.status_code, "UNKNOWN_ERROR")
    
    return error_response(
        message=str(exc.detail) if isinstance(exc.detail, str) else "An error occurred",
        error_code=error_code,
        detail=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id
    )


def handle_generic_exception(
    exc: Exception,
    message: str = "An unexpected error occurred",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert generic exception to standardized error response.
    
    Args:
        exc: Any Python exception
        message: Human-readable error message
        request_id: Optional request ID
        
    Returns:
        Standardized error response dictionary
    """
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return error_response(
        message=message,
        error_code="INTERNAL_ERROR",
        detail=str(exc),
        status_code=500,
        request_id=request_id
    )


# Common error response builders
def not_found_response(
    resource: str,
    identifier: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standard 404 not found response."""
    return error_response(
        message=f"{resource} not found",
        error_code="NOT_FOUND",
        detail=f"No {resource.lower()} found with identifier: {identifier}",
        status_code=404,
        request_id=request_id
    )


def validation_error_response(
    field: str,
    detail: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standard validation error response."""
    return error_response(
        message="Validation error",
        error_code="VALIDATION_ERROR",
        detail=detail,
        status_code=422,
        field=field,
        request_id=request_id
    )


def unauthorized_response(
    detail: str = "Authentication required",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standard 401 unauthorized response."""
    return error_response(
        message="Unauthorized",
        error_code="UNAUTHORIZED",
        detail=detail,
        status_code=401,
        request_id=request_id
    )


def forbidden_response(
    detail: str = "Access denied",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standard 403 forbidden response."""
    return error_response(
        message="Forbidden",
        error_code="FORBIDDEN",
        detail=detail,
        status_code=403,
        request_id=request_id
    )

