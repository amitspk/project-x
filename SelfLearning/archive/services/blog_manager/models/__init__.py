"""
Data models for the blog manager microservice.

Contains Pydantic models for request/response validation and MongoDB document models.
"""

from .request_models import BlogUrlRequest, BlogLookupRequest
from .response_models import (
    BlogQuestionsResponse,
    QuestionModel,
    ErrorResponse,
    HealthResponse,
    BlogInfoModel
)
from .mongodb_models import BlogDocument, QuestionDocument, SummaryDocument

__all__ = [
    # Request Models
    "BlogUrlRequest",
    "BlogLookupRequest",
    
    # Response Models
    "BlogQuestionsResponse",
    "QuestionModel",
    "ErrorResponse",
    "HealthResponse",
    "BlogInfoModel",
    
    # MongoDB Models
    "BlogDocument",
    "QuestionDocument",
    "SummaryDocument"
]
