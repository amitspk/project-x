"""Job models for Worker service."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enum."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class JobResult(BaseModel):
    """Result of a completed job."""
    summary_id: Optional[str] = None
    question_count: int = 0
    embedding_count: int = 0
    processing_details: Optional[Dict[str, Any]] = None


class ProcessingJob(BaseModel):
    """Processing job model."""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    blog_url: str
    publisher_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: JobStatus = JobStatus.QUEUED
    failure_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Processing metadata
    processing_time_seconds: Optional[float] = None
    result: Optional[JobResult] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

