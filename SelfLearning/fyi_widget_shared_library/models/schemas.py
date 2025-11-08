"""
Pydantic models for Content Processing Service.

Request/response schemas for API endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# Request Models
# ============================================================================

class ProcessBlogRequest(BaseModel):
    """Request to process a blog URL."""
    url: str = Field(..., description="Blog URL to process")
    num_questions: int = Field(default=5, ge=1, le=20, description="Number of questions to generate")
    force_refresh: bool = Field(default=False, description="Force re-processing even if already exists")


class GetQuestionsRequest(BaseModel):
    """Request to get questions for a blog."""
    blog_url: str = Field(..., description="Blog URL")
    limit: int = Field(default=10, ge=1, le=50)


class SearchSimilarRequest(BaseModel):
    """Request to search for similar blogs."""
    question_id: str = Field(..., description="Question ID to find similar blogs for")
    limit: int = Field(default=3, ge=1, le=10)


# ============================================================================
# Response Models
# ============================================================================

class BlogContentResponse(BaseModel):
    """Response containing blog content."""
    url: str
    title: str
    content: str
    language: str
    word_count: int
    created_at: datetime
    

class QuestionAnswerPair(BaseModel):
    """A question-answer pair."""
    id: str
    question: str
    answer: str
    blog_url: str
    blog_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: datetime


class BlogSummary(BaseModel):
    """Blog summary response."""
    blog_id: str
    blog_url: str
    summary: str
    key_points: List[str]
    embedding: Optional[List[float]] = None
    created_at: datetime


class ProcessingResult(BaseModel):
    """Result of blog processing."""
    blog_url: str
    blog_id: str
    status: str
    summary: BlogSummary
    questions: List[QuestionAnswerPair]
    processing_time_ms: int
    message: str


class SimilarBlog(BaseModel):
    """Similar blog information."""
    url: str
    title: str
    similarity_score: float


class SearchSimilarResponse(BaseModel):
    """Response for similar blog search."""
    question_id: str
    question_text: str
    similar_blogs: List[SimilarBlog]


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: datetime
    database: Dict[str, Any]
    llm: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Internal Models (for service communication)
# ============================================================================

class CrawledContent(BaseModel):
    """Crawled content from web."""
    url: str
    title: str
    content: str
    language: str
    word_count: int
    metadata: Dict[str, Any] = {}


class LLMGenerationResult(BaseModel):
    """Result from LLM generation."""
    text: str
    tokens_used: int
    model: str
    provider: str


class EmbeddingResult(BaseModel):
    """Result from embedding generation."""
    embedding: List[float]
    dimensions: int
    model: str

