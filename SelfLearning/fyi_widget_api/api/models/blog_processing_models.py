"""Pydantic models for blog processing queue and audit collections."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class BlogProcessingStatus(str, Enum):
    """Status enum for blog processing queue."""
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRY = "retry"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditStatus(str, Enum):
    """Status enum for audit entries (final states only)."""
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# BLOG PROCESSING QUEUE MODELS
# ============================================================================

class BlogProcessingQueueEntry(BaseModel):
    """
    Model for blog_processing_queue collection entry.
    
    Represents the current processing state of a blog.
    """
    url: str = Field(..., description="Blog URL (normalized)")
    publisher_id: str = Field(..., description="Publisher ID")
    status: BlogProcessingStatus = Field(..., description="Current processing status")
    attempt_count: int = Field(0, description="Number of processing attempts (0-3)")
    
    current_job_id: Optional[str] = Field(None, description="Current/latest job ID")
    worker_id: Optional[str] = Field(None, description="Worker instance processing this")
    
    last_error: Optional[str] = Field(None, description="Last error message")
    error_type: Optional[str] = Field(None, description="Error category")
    
    heartbeat_at: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    heartbeat_interval_seconds: int = Field(30, description="Expected heartbeat interval")
    
    created_at: datetime = Field(..., description="When entry was created")
    updated_at: datetime = Field(..., description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="When current attempt started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    
    healed: bool = Field(False, description="True if auto-created/fixed by API")
    reprocessed_count: int = Field(0, description="Number of manual reprocesses")
    last_reprocessed_at: Optional[datetime] = Field(None, description="Last reprocess timestamp")
    tags: List[str] = Field(default_factory=list, description="Optional tags")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "publisher_id": "pub_abc123",
                "status": "processing",
                "attempt_count": 1,
                "current_job_id": "uuid-xxx-yyy",
                "worker_id": "worker-instance-1",
                "last_error": None,
                "error_type": None,
                "heartbeat_at": "2025-01-02T10:30:00Z",
                "heartbeat_interval_seconds": 30,
                "created_at": "2025-01-02T10:00:00Z",
                "updated_at": "2025-01-02T10:30:00Z",
                "started_at": "2025-01-02T10:05:00Z",
                "completed_at": None,
                "healed": False,
                "reprocessed_count": 0,
                "last_reprocessed_at": None,
                "tags": []
            }
        }


class BlogProcessingQueueStats(BaseModel):
    """Statistics for blog processing queue."""
    queued: int = Field(0, description="Number of queued jobs")
    processing: int = Field(0, description="Number of processing jobs")
    retry: int = Field(0, description="Number of jobs awaiting retry")
    completed: int = Field(0, description="Number of completed jobs")
    failed: int = Field(0, description="Number of permanently failed jobs")
    total: int = Field(0, description="Total number of jobs")


# ============================================================================
# BLOG PROCESSING AUDIT MODELS
# ============================================================================

class BlogProcessingAuditEntry(BaseModel):
    """
    Model for blog_processing_audit collection entry.
    
    Represents a completed processing attempt (successful or failed).
    """
    url: str = Field(..., description="Blog URL")
    publisher_id: str = Field(..., description="Publisher ID")
    job_id: str = Field(..., description="Job ID from processing_jobs")
    worker_id: str = Field(..., description="Worker instance that processed")
    
    status: AuditStatus = Field(..., description="Final status (completed or failed)")
    attempt_number: int = Field(..., description="Which attempt this was (1-3)")
    
    processing_time_seconds: float = Field(..., description="Processing duration")
    started_at: datetime = Field(..., description="When processing started")
    completed_at: datetime = Field(..., description="When processing completed/failed")
    created_at: datetime = Field(..., description="Audit entry creation timestamp")
    
    # Success fields (optional)
    question_count: Optional[int] = Field(None, description="Questions generated")
    summary_length: Optional[int] = Field(None, description="Summary character count")
    embedding_count: Optional[int] = Field(None, description="Embeddings created")
    
    # Failure fields (optional)
    error_message: Optional[str] = Field(None, description="Error message")
    error_type: Optional[str] = Field(None, description="Error category")
    error_stack_trace: Optional[str] = Field(None, description="Full stack trace")
    
    # Blog metadata (optional)
    blog_title: Optional[str] = Field(None, description="Blog title")
    blog_content_length: Optional[int] = Field(None, description="Content length")
    blog_author: Optional[str] = Field(None, description="Blog author")
    
    # Configuration snapshot (optional)
    llm_model: Optional[str] = Field(None, description="LLM model used")
    embedding_model: Optional[str] = Field(None, description="Embedding model used")
    publisher_config: Optional[Dict[str, Any]] = Field(None, description="Publisher config")
    
    # Reprocessing context (optional)
    is_reprocess: bool = Field(False, description="True if manual reprocess")
    reprocess_reason: Optional[str] = Field(None, description="Reprocess reason")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "publisher_id": "pub_abc123",
                "job_id": "uuid-xxx-yyy",
                "worker_id": "worker-instance-1",
                "status": "completed",
                "attempt_number": 1,
                "processing_time_seconds": 37.5,
                "started_at": "2025-01-02T10:05:00Z",
                "completed_at": "2025-01-02T10:05:37Z",
                "created_at": "2025-01-02T10:05:37Z",
                "question_count": 5,
                "summary_length": 346,
                "embedding_count": 6,
                "error_message": None,
                "error_type": None,
                "blog_title": "Example Article",
                "blog_content_length": 2580,
                "llm_model": "gpt-4o-mini",
                "embedding_model": "text-embedding-3-large",
                "is_reprocess": False
            }
        }


class BlogProcessingAuditStats(BaseModel):
    """Statistics from audit trail."""
    completed: int = Field(0, description="Successful completions")
    failed: int = Field(0, description="Failed attempts")
    total: int = Field(0, description="Total audit entries")
    avg_processing_time_completed: float = Field(0.0, description="Avg time for completed")
    avg_processing_time_failed: float = Field(0.0, description="Avg time for failed")
    total_questions_generated: int = Field(0, description="Total questions generated")


class ErrorTypeAnalysis(BaseModel):
    """Error type analysis from audit trail."""
    error_type: str = Field(..., description="Error category")
    count: int = Field(..., description="Number of occurrences")
    example_error: Optional[str] = Field(None, description="Example error message")


class FailureAnalysis(BaseModel):
    """Failure pattern analysis."""
    total_failures: int = Field(0, description="Total number of failures")
    error_types: List[ErrorTypeAnalysis] = Field(default_factory=list, description="Error breakdown")

