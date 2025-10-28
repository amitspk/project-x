"""
Custom exceptions for the blog manager microservice.

Defines application-specific exceptions with proper error codes and messages.
"""

from typing import Optional, Dict, Any


class BlogManagerException(Exception):
    """Base exception for blog manager microservice."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "BLOG_MANAGER_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BlogNotFoundException(BlogManagerException):
    """Raised when a blog is not found."""
    
    def __init__(self, identifier: str, identifier_type: str = "URL"):
        message = f"Blog not found for {identifier_type}: {identifier}"
        super().__init__(
            message=message,
            error_code="BLOG_NOT_FOUND",
            status_code=404,
            details={"identifier": identifier, "identifier_type": identifier_type}
        )


class InvalidUrlException(BlogManagerException):
    """Raised when an invalid URL is provided."""
    
    def __init__(self, url: str):
        message = f"Invalid URL format: {url}"
        super().__init__(
            message=message,
            error_code="INVALID_URL",
            status_code=400,
            details={"url": url}
        )


class DatabaseConnectionException(BlogManagerException):
    """Raised when database connection fails."""
    
    def __init__(self, details: str = ""):
        message = f"Database connection failed: {details}"
        super().__init__(
            message=message,
            error_code="DATABASE_CONNECTION_ERROR",
            status_code=503,
            details={"connection_details": details}
        )


class NoQuestionsFoundException(BlogManagerException):
    """Raised when no questions are found for a blog."""
    
    def __init__(self, blog_id: str):
        message = f"No questions found for blog: {blog_id}"
        super().__init__(
            message=message,
            error_code="NO_QUESTIONS_FOUND",
            status_code=404,
            details={"blog_id": blog_id}
        )


class ValidationException(BlogManagerException):
    """Raised when request validation fails."""
    
    def __init__(self, field: str, value: Any, reason: str):
        message = f"Validation failed for field '{field}': {reason}"
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, "value": str(value), "reason": reason}
        )


class RateLimitExceededException(BlogManagerException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window: int):
        message = f"Rate limit exceeded: {limit} requests per {window} seconds"
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"limit": limit, "window": window}
        )


class CacheException(BlogManagerException):
    """Raised when cache operations fail."""
    
    def __init__(self, operation: str, details: str = ""):
        message = f"Cache {operation} failed: {details}"
        super().__init__(
            message=message,
            error_code="CACHE_ERROR",
            status_code=500,
            details={"operation": operation, "details": details}
        )
