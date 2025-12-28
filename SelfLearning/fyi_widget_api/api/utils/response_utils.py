"""
Utility functions for generating standardized API responses.

Provides helper functions to create consistent responses across all endpoints.
"""

import uuid
import logging
from typing import Any, Optional, List, Dict
from datetime import datetime
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from fyi_widget_api.api.models.response_models import (
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
    Create a JSONResponse with the given data and status code.
    
    Args:
        data: Response data dictionary
        status_code: HTTP status code
        
    Returns:
        JSONResponse instance
    """
    return JSONResponse(content=data, status_code=status_code)


def success_json_response(
    result: Any,
    message: str = "Operation completed successfully",
    status_code: int = 200,
    metadata: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a JSONResponse with standardized success format.
    
    Args:
        result: The response data
        message: Human-readable success message
        status_code: HTTP status code
        metadata: Optional metadata
        warnings: Optional list of warnings
        request_id: Optional request ID
        
    Returns:
        JSONResponse instance
    """
    data = success_response(
        result=result,
        message=message,
        status_code=status_code,
        metadata=metadata,
        warnings=warnings,
        request_id=request_id
    )
    return create_json_response(data, status_code)


def error_json_response(
    message: str,
    error_code: str,
    detail: str,
    status_code: int = 400,
    field: Optional[str] = None,
    warnings: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a JSONResponse with standardized error format.
    
    Args:
        message: Human-readable error message
        error_code: Machine-readable error code
        detail: Detailed error description
        status_code: HTTP status code
        field: Optional field name for validation errors
        warnings: Optional list of warnings
        request_id: Optional request ID
        
    Returns:
        JSONResponse instance
    """
    data = error_response(
        message=message,
        error_code=error_code,
        detail=detail,
        status_code=status_code,
        field=field,
        warnings=warnings,
        request_id=request_id
    )
    return create_json_response(data, status_code)


def handle_http_exception(
    exc: HTTPException,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert FastAPI HTTPException to standardized error response.
    
    Args:
        exc: HTTPException instance
        request_id: Optional request ID
        
    Returns:
        Dictionary containing standardized error response
    """
    if request_id is None:
        request_id = generate_request_id()
    
    # Try to extract error code and detail from exception
    error_code = "HTTP_ERROR"
    detail = str(exc.detail) if exc.detail else "An error occurred"
    
    # If detail is a dict, extract code and detail
    if isinstance(exc.detail, dict):
        error_code = exc.detail.get("error", {}).get("code", "HTTP_ERROR")
        detail = exc.detail.get("error", {}).get("detail", str(exc.detail))
        field = exc.detail.get("error", {}).get("field")
    else:
        field = None
    
    return error_response(
        message=str(exc.detail) if not isinstance(exc.detail, dict) else detail,
        error_code=error_code,
        detail=detail,
        status_code=exc.status_code,
        field=field,
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
        exc: Exception instance
        message: Human-readable error message
        request_id: Optional request ID
        
    Returns:
        Dictionary containing standardized error response
    """
    if request_id is None:
        request_id = generate_request_id()
    
    logger.error(f"[{request_id}] Unexpected error: {exc}", exc_info=True)
    
    return error_response(
        message=message,
        error_code="INTERNAL_ERROR",
        detail=str(exc),
        status_code=500,
        request_id=request_id
    )


def not_found_response(
    resource: str,
    identifier: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized 404 Not Found response.
    
    Args:
        resource: Resource type (e.g., "Question", "Blog")
        identifier: Resource identifier
        request_id: Optional request ID
        
    Returns:
        Dictionary containing standardized error response
    """
    return error_response(
        message=f"{resource} not found",
        error_code="NOT_FOUND",
        detail=f"{resource} with identifier '{identifier}' was not found",
        status_code=404,
        request_id=request_id
    )


def validation_error_response(
    message: str,
    detail: str,
    field: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized 400 Validation Error response.
    
    Args:
        message: Human-readable error message
        detail: Detailed validation error description
        field: Field name that failed validation
        request_id: Optional request ID
        
    Returns:
        Dictionary containing standardized error response
    """
    return error_response(
        message=message,
        error_code="VALIDATION_ERROR",
        detail=detail,
        status_code=400,
        field=field,
        request_id=request_id
    )


def unauthorized_response(
    message: str = "Authentication required",
    detail: str = "Valid API key is required to access this resource",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized 401 Unauthorized response.
    
    Args:
        message: Human-readable error message
        detail: Detailed error description
        request_id: Optional request ID
        
    Returns:
        Dictionary containing standardized error response
    """
    return error_response(
        message=message,
        error_code="UNAUTHORIZED",
        detail=detail,
        status_code=401,
        request_id=request_id
    )


def forbidden_response(
    message: str = "Access forbidden",
    detail: str = "You do not have permission to access this resource",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized 403 Forbidden response.
    
    Args:
        message: Human-readable error message
        detail: Detailed error description
        request_id: Optional request ID
        
    Returns:
        Dictionary containing standardized error response
    """
    return error_response(
        message=message,
        error_code="FORBIDDEN",
        detail=detail,
        status_code=403,
        request_id=request_id
    )

