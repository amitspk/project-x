"""
Swagger/OpenAPI response models for API documentation.

These models are used to generate accurate API documentation
with proper response schemas for UI developers.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from fyi_widget_worker_service.services.llm_providers.model_config import LLMModelConfig


# ============================================================================
# Base Response Models
# ============================================================================

class ErrorDetailSchema(BaseModel):
    """Error detail schema for Swagger."""
    code: str = Field(..., example="NOT_FOUND")
    detail: str = Field(..., example="Resource not found")
    field: Optional[str] = Field(None, example="blog_url")


class ResponseMetadataSchema(BaseModel):
    """Metadata schema for list responses."""
    total: int = Field(..., example=100)
    page: int = Field(..., example=1)
    page_size: int = Field(..., example=10)


class StandardSuccessResponse(BaseModel):
    """Standard success response schema."""
    status: str = Field("success", example="success")
    status_code: int = Field(..., example=200)
    message: str = Field(..., example="Operation successful")
    result: Dict[str, Any] = Field(..., example={})
    metadata: Optional[ResponseMetadataSchema] = None
    warnings: Optional[List[str]] = None
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class StandardErrorResponse(BaseModel):
    """Standard error response schema."""
    status: str = Field("error", example="error")
    status_code: int = Field(..., example=404)
    message: str = Field(..., example="Resource not found")
    error: ErrorDetailSchema
    warnings: Optional[List[str]] = None
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


# ============================================================================
# Questions Endpoints
# ============================================================================

class QuestionSchema(BaseModel):
    """Question schema for API responses."""
    id: str = Field(..., example="507f1f77bcf86cd799439011")
    question: str = Field(..., example="What is the main topic of this article?")
    answer: str = Field(..., example="The article discusses...")
    blog_url: str = Field(..., example="https://example.com/article")
    blog_id: Optional[str] = Field(None, example="507f1f77bcf86cd799439012")
    created_at: str = Field(..., example="2025-10-18T14:30:00.123456")


class QuestionsByUrlResponse(BaseModel):
    """Response for getting questions by URL."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Questions retrieved successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "blog_url": "https://example.com/article",
            "questions": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "question": "What is the main topic?",
                    "answer": "The article discusses...",
                    "blog_url": "https://example.com/article",
                    "created_at": "2025-10-18T14:30:00.123456"
                }
            ],
            "blog_info": {
                "title": "Example Article",
                "url": "https://example.com/article",
                "word_count": 1000
            }
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class QuestionByIdResponse(BaseModel):
    """Response for getting a single question by ID."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Question retrieved successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "id": "507f1f77bcf86cd799439011",
            "question": "What is the main topic?",
            "answer": "The article discusses...",
            "blog_url": "https://example.com/article",
            "created_at": "2025-10-18T14:30:00.123456"
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class CheckAndLoadResponse(BaseModel):
    """Response for check and load questions endpoint."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Processing started")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "processing_status": "not_started",
            "blog_url": "https://example.com/article",
            "questions": None,
            "blog_info": None,
            "job_id": "job_abc123",
            "message": "Processing started - check back in 30-60 seconds"
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


# ============================================================================
# Jobs Endpoints
# ============================================================================

class ProcessJobResponse(BaseModel):
    """Response for processing a blog job."""
    status: str = Field("success", example="success")
    status_code: int = Field(202, example=202)
    message: str = Field(..., example="Blog processing job enqueued successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "job_id": "job_abc123",
            "blog_url": "https://example.com/article",
            "status": "queued",
            "created_at": "2025-10-18T14:30:00.123456"
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class JobStatusResponse(BaseModel):
    """Response for job status."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Job status retrieved successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "job_id": "job_abc123",
            "blog_url": "https://example.com/article",
            "status": "completed",
            "failure_count": 0,
            "created_at": "2025-10-18T14:30:00.123456",
            "started_at": "2025-10-18T14:30:05.123456",
            "completed_at": "2025-10-18T14:30:30.123456",
            "processing_time_seconds": 25.0,
            "result": {
                "summary_id": "summary_abc123",
                "question_count": 20,
                "embedding_count": 21
            }
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class JobStatsResponse(BaseModel):
    """Response for job statistics."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Job statistics retrieved successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "queued": 10,
            "processing": 2,
            "completed": 100,
            "failed": 5,
            "skipped": 3
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


# ============================================================================
# Q&A Endpoint
# ============================================================================

class QAResponse(BaseModel):
    """Response for Q&A endpoint."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Question answered successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "question": "What is machine learning?",
            "answer": "Machine learning is a subset of artificial intelligence...",
            "processing_time_ms": 1250,
            "word_count": 150,
            "model": "gpt-4o-mini"
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


# ============================================================================
# Search Endpoint
# ============================================================================

class SimilarBlogSchema(BaseModel):
    """Similar blog schema."""
    url: str = Field(..., example="https://example.com/article2")
    title: str = Field(..., example="Related Article")
    similarity_score: float = Field(..., example=0.95)


class SearchResponse(BaseModel):
    """Response for similarity search."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Similar blogs found successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "question_id": "507f1f77bcf86cd799439011",
            "question_text": "What is the main topic?",
            "similar_blogs": [
                {
                    "url": "https://example.com/article2",
                    "title": "Related Article",
                    "similarity_score": 0.95
                }
            ]
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


# ============================================================================
# Publishers Endpoints
# ============================================================================

class PublisherConfigSchema(BaseModel):
    """Publisher configuration schema."""
    questions_per_blog: int = Field(20, example=20)
    daily_blog_limit: int = Field(..., example=100)
    max_total_blogs: int | None = Field(None, example=500, description="Maximum total blogs allowed (null for unlimited)")
    threshold_before_processing_blog: int = Field(0, example=0, description="Threshold value before processing a blog. Defaults to 0 when publisher is onboarded.")
    summary_model: str = Field(..., example="gpt-4o-mini")
    questions_model: str = Field(..., example="gpt-4o-mini")
    chat_model: str = Field(..., example="gpt-4o-mini")
    summary_temperature: float = Field(0.7, example=0.7)
    questions_temperature: float = Field(0.7, example=0.7)
    chat_temperature: float = Field(0.7, example=0.7)
    summary_max_tokens: int = Field(2000, example=2000)
    questions_max_tokens: int = Field(20000, example=20000)
    chat_max_tokens: int = Field(300, example=300)
    custom_question_prompt: Optional[str] = None
    custom_summary_prompt: Optional[str] = None
    use_grounding: bool = Field(False, example=False)
    widget: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "gaTrackingId": "G-WPWFCMCSS3",
            "adsense": {
                "enabled": False,
                "pubId": "partner-pub-XXXXX",
            }
        }
    )


class PublisherMetadataSchema(BaseModel):
    """Publisher metadata schema."""
    total_blogs_processed: int = Field(0, example=50)
    total_questions_generated: int = Field(0, example=1000)
    blog_slots_reserved: int = Field(0, example=2, description="Number of blog processing slots currently reserved")
    subscription_tier: str = Field("free", example="free")
    created_at: str = Field(..., example="2025-10-18T14:30:00.123456")
    updated_at: str = Field(..., example="2025-10-18T14:30:00.123456")
    last_active_at: Optional[str] = Field(None, example="2025-10-18T14:30:00.123456")


class PublisherOnboardResponse(BaseModel):
    """Response for publisher onboarding."""
    status: str = Field("success", example="success")
    status_code: int = Field(201, example=201)
    message: str = Field(..., example="Publisher onboarded successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "id": "pub_abc123",
            "name": "Example Publisher",
            "domain": "example.com",
            "email": "publisher@example.com",
            "api_key": "pub_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "status": "trial",
            "config": {
                "questions_per_blog": 20,
                "daily_blog_limit": 100
            },
            "metadata": {
                "total_blogs_processed": 0,
                "total_questions_generated": 0,
                "blog_slots_reserved": 0,
                "subscription_tier": "free"
            }
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class PublisherGetResponse(BaseModel):
    """Response for getting a publisher."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Publisher retrieved successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "id": "pub_abc123",
            "name": "Example Publisher",
            "domain": "example.com",
            "email": "publisher@example.com",
            "status": "active",
            "config": {},
            "metadata": {}
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class PublishersListResponse(BaseModel):
    """Response for listing publishers."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Publishers retrieved successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "publishers": [
                {
                    "id": "pub_abc123",
                    "name": "Example Publisher",
                    "domain": "example.com",
                    "status": "active"
                }
            ],
            "metadata": {
                "total": 100,
                "page": 1,
                "page_size": 50
            }
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class PublisherUpdateResponse(BaseModel):
    """Response for updating a publisher."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Publisher updated successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "id": "pub_abc123",
            "name": "Updated Publisher",
            "domain": "example.com",
            "status": "active",
            "config": {}
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class PublisherDeleteResponse(BaseModel):
    """Response for deleting a publisher."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Publisher deleted successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "id": "pub_abc123",
            "deleted": True
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class PublisherConfigResponse(BaseModel):
    """Response for getting/updating publisher config."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Publisher configuration retrieved successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "publisher_id": "pub_abc123",
            "config": {
                "questions_per_blog": 20,
                "daily_blog_limit": 100
            }
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class PublisherRegenerateApiKeyResponse(BaseModel):
    """Response for regenerating publisher API key."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="API key regenerated successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "publisher_id": "pub_abc123",
            "new_api_key": "pub_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")


class PublisherMetadataResponse(BaseModel):
    """Response for getting publisher metadata."""
    status: str = Field("success", example="success")
    status_code: int = Field(200, example=200)
    message: str = Field(..., example="Publisher metadata retrieved successfully")
    result: Dict[str, Any] = Field(
        ...,
        example={
            "publisher_id": "pub_abc123",
            "metadata": {
                "total_blogs_processed": 50,
                "total_questions_generated": 1000,
                "blog_slots_reserved": 2,
                "subscription_tier": "free"
            }
        }
    )
    request_id: str = Field(..., example="req_abc123def456")
    timestamp: str = Field(..., example="2025-10-18T14:30:00.123456")

