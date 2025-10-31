"""
Standardized API Response Models.

Provides consistent response format across all API endpoints.
"""

from typing import Optional, Any, Dict, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Error detail information."""
    code: str = Field(..., description="Machine-readable error code")
    detail: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field name for validation errors")


class ResponseMetadata(BaseModel):
    """Optional metadata for responses (pagination, counts, etc.)."""
    total: Optional[int] = Field(None, description="Total number of items")
    page: Optional[int] = Field(None, description="Current page number")
    page_size: Optional[int] = Field(None, description="Items per page")
    has_more: Optional[bool] = Field(None, description="Whether more items exist")
    

class StandardResponse(BaseModel):
    """
    Standard API response format for all endpoints.
    
    Success Example:
    {
        "status": "success",
        "status_code": 200,
        "message": "Questions retrieved successfully",
        "result": {...},
        "request_id": "req_abc123",
        "timestamp": "2025-10-18T14:30:00.123Z"
    }
    
    Error Example:
    {
        "status": "error",
        "status_code": 404,
        "message": "Resource not found",
        "error": {
            "code": "NOT_FOUND",
            "detail": "No questions found for URL: https://...",
            "field": "blog_url"
        },
        "request_id": "req_abc123",
        "timestamp": "2025-10-18T14:30:00.123Z"
    }
    """
    status: Literal["success", "error"] = Field(..., description="Response status")
    status_code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Human-readable message")
    result: Optional[Any] = Field(None, description="Response data for success")
    error: Optional[ErrorDetail] = Field(None, description="Error details for failures")
    metadata: Optional[ResponseMetadata] = Field(None, description="Optional metadata")
    warnings: Optional[List[str]] = Field(None, description="Non-fatal warnings")
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example_success": {
                "status": "success",
                "status_code": 200,
                "message": "Operation completed successfully",
                "result": {"data": "example"},
                "request_id": "req_abc123xyz",
                "timestamp": "2025-10-18T14:30:00.123456Z"
            },
            "example_error": {
                "status": "error",
                "status_code": 404,
                "message": "Resource not found",
                "error": {
                    "code": "NOT_FOUND",
                    "detail": "The requested resource does not exist",
                    "field": "id"
                },
                "request_id": "req_abc123xyz",
                "timestamp": "2025-10-18T14:30:00.123456Z"
            }
        }


class SuccessResponse(StandardResponse):
    """Success response model."""
    status: Literal["success"] = "success"
    result: Any = Field(..., description="Response data")
    error: None = None


class ErrorResponse(StandardResponse):
    """Error response model."""
    status: Literal["error"] = "error"
    error: ErrorDetail = Field(..., description="Error details")
    result: None = None

