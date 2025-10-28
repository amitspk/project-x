"""
Response models for the blog manager microservice.

Pydantic models for API response validation and serialization.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class QuestionModel(BaseModel):
    """Model for a single question and answer."""
    
    id: str = Field(..., description="Unique question identifier")
    question: str = Field(..., description="The question text")
    answer: str = Field(..., description="The answer text")
    question_type: str = Field(..., description="Type of question (e.g., factual, analytical)")
    difficulty_level: Optional[str] = Field(default=None, description="Question difficulty level")
    question_order: int = Field(..., description="Order of question in the set")
    confidence_score: Optional[float] = Field(default=None, description="AI confidence score")
    estimated_answer_time: Optional[int] = Field(default=None, description="Estimated time to answer in seconds")
    
    # Optional metadata fields
    topic_area: Optional[str] = Field(default=None, description="Topic area of the question")
    bloom_taxonomy_level: Optional[str] = Field(default=None, description="Bloom's taxonomy level")
    learning_objective: Optional[str] = Field(default=None, description="Learning objective")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "q1",
                "question": "What are the potential risks of not using ThreadLocal in a multi-threaded Java application?",
                "answer": "Not using ThreadLocal can lead to data inconsistency and race conditions...",
                "question_type": "cause and effect",
                "difficulty_level": "intermediate",
                "question_order": 1,
                "confidence_score": 0.9,
                "estimated_answer_time": 30
            }
        }
    }


class BlogInfoModel(BaseModel):
    """Model for blog information."""
    
    blog_id: str = Field(..., description="Internal blog identifier")
    title: str = Field(..., description="Blog title")
    url: str = Field(..., description="Blog URL")
    author: Optional[str] = Field(default=None, description="Blog author")
    published_date: Optional[datetime] = Field(default=None, description="Publication date")
    word_count: Optional[int] = Field(default=None, description="Word count")
    source_domain: Optional[str] = Field(default=None, description="Source domain")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "blog_id": "effective_use_of_threadlocal_in_java_app_5bbb34ce",
                "title": "Effective Use of ThreadLocal in Java Applications",
                "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
                "author": "Alex Klimenko",
                "word_count": 3659,
                "source_domain": "medium.com"
            }
        }
    }


class SummaryModel(BaseModel):
    """Model for blog summary."""
    
    summary_text: str = Field(..., description="Summary text")
    key_points: List[str] = Field(default=[], description="Key points from the blog")
    main_topics: List[str] = Field(default=[], description="Main topics covered")
    confidence_score: Optional[float] = Field(default=None, description="Summary confidence score")
    word_count: Optional[int] = Field(default=None, description="Summary word count")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "summary_text": "The article explores ThreadLocal in Java applications...",
                "key_points": [
                    "ThreadLocal provides thread-local variables",
                    "Prevents data sharing issues among threads"
                ],
                "main_topics": ["Java", "Concurrency", "Thread Safety"],
                "confidence_score": 0.9,
                "word_count": 131
            }
        }
    }


class BlogQuestionsResponse(BaseModel):
    """Response model for blog questions API."""
    
    success: bool = Field(default=True, description="Request success status")
    blog_info: BlogInfoModel = Field(..., description="Blog information")
    questions: List[QuestionModel] = Field(..., description="List of questions and answers")
    summary: Optional[SummaryModel] = Field(default=None, description="Blog summary (if requested)")
    
    # Metadata
    total_questions: int = Field(..., description="Total number of questions")
    returned_questions: int = Field(..., description="Number of questions returned")
    has_more: bool = Field(default=False, description="Whether more questions are available")
    
    # Generation metadata
    generated_at: Optional[datetime] = Field(default=None, description="When questions were generated")
    ai_model: Optional[str] = Field(default=None, description="AI model used for generation")
    average_confidence: Optional[float] = Field(default=None, description="Average confidence score")
    
    # Request metadata
    request_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        },
        "json_schema_extra": {
            "example": {
                "success": True,
                "blog_info": {
                    "blog_id": "effective_use_of_threadlocal_in_java_app_5bbb34ce",
                    "title": "Effective Use of ThreadLocal in Java Applications",
                    "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
                    "author": "Alex Klimenko",
                    "word_count": 3659
                },
                "questions": [
                    {
                        "id": "q1",
                        "question": "What are the potential risks of not using ThreadLocal?",
                        "answer": "Not using ThreadLocal can lead to data inconsistency...",
                        "question_type": "cause and effect",
                        "question_order": 1,
                        "confidence_score": 0.9
                    }
                ],
                "total_questions": 10,
                "returned_questions": 10,
                "has_more": False,
                "ai_model": "gpt-4",
                "average_confidence": 0.87
            }
        }
    }


class ErrorResponse(BaseModel):
    """Response model for API errors."""
    
    success: bool = Field(default=False, description="Request success status")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request identifier for tracking")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        },
        "json_schema_extra": {
            "example": {
                "success": False,
                "error_code": "BLOG_NOT_FOUND",
                "message": "Blog not found for URL: https://example.com/nonexistent",
                "details": {
                    "identifier": "https://example.com/nonexistent",
                    "identifier_type": "URL"
                },
                "timestamp": "2025-10-02T20:52:42.869Z"
            }
        }
    }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: str = Field(..., description="Service version")
    database_status: str = Field(..., description="Database connection status")
    uptime_seconds: Optional[float] = Field(default=None, description="Service uptime in seconds")
    
    # Optional detailed health information
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed health information")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        },
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2025-10-02T20:52:42.869Z",
                "version": "1.0.0",
                "database_status": "connected",
                "uptime_seconds": 3600.5,
                "details": {
                    "database_collections": 4,
                    "total_blogs": 156,
                    "total_questions": 1560
                }
            }
        }
    }


class QuestionAnswerResponse(BaseModel):
    """Response model for general Q&A endpoint."""
    
    success: bool = Field(default=True, description="Request success status")
    question: str = Field(..., description="The original question")
    answer: str = Field(..., description="AI-generated answer")
    
    # Response metadata
    word_count: int = Field(..., description="Number of words in the answer")
    character_count: int = Field(..., description="Number of characters in the answer")
    ai_model: Optional[str] = Field(default=None, description="AI model used for generation")
    
    # Processing metadata
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")
    request_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        },
        "json_schema_extra": {
            "example": {
                "success": True,
                "question": "What are the benefits of using microservices architecture?",
                "answer": "Microservices architecture offers several key benefits: 1) **Scalability** - Individual services can be scaled independently based on demand. 2) **Technology Diversity** - Teams can choose the best technology stack for each service. 3) **Fault Isolation** - If one service fails, others continue operating. 4) **Faster Development** - Small, focused teams can develop and deploy services independently. 5) **Easier Maintenance** - Smaller codebases are easier to understand and modify. However, microservices also introduce complexity in service communication, data consistency, and deployment orchestration.",
                "word_count": 89,
                "character_count": 567,
                "ai_model": "gpt-4",
                "processing_time_ms": 1250.5
            }
        }
    }


class SimilarBlogModel(BaseModel):
    """Model for a similar blog result."""
    
    blog_id: str = Field(..., description="Internal blog identifier")
    title: str = Field(..., description="Blog title")
    url: str = Field(..., description="Blog URL")
    similarity_score: float = Field(..., description="Similarity score (0.0 to 1.0)")
    summary_snippet: Optional[str] = Field(default=None, description="Brief summary snippet")
    author: Optional[str] = Field(default=None, description="Blog author")
    published_date: Optional[datetime] = Field(default=None, description="Publication date")
    word_count: Optional[int] = Field(default=None, description="Blog word count")
    source_domain: Optional[str] = Field(default=None, description="Source domain")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        },
        "json_schema_extra": {
            "example": {
                "blog_id": "microservices_best_practices_abc123",
                "title": "Microservices Best Practices for Enterprise Applications",
                "url": "https://dev.to/author/microservices-best-practices",
                "similarity_score": 0.87,
                "summary_snippet": "This article explores advanced microservices patterns and best practices...",
                "author": "John Developer",
                "word_count": 2500,
                "source_domain": "dev.to"
            }
        }
    }


class SimilarBlogsResponse(BaseModel):
    """Response model for similar blogs endpoint."""
    
    success: bool = Field(default=True, description="Request success status")
    question_id: str = Field(..., description="The question ID that was searched")
    question_text: str = Field(..., description="The question text")
    answer_text: str = Field(..., description="The answer text")
    similar_blogs: List[SimilarBlogModel] = Field(..., description="List of similar blogs")
    
    # Search metadata
    total_found: int = Field(..., description="Total number of similar blogs found")
    search_embedding_size: int = Field(..., description="Size of the search embedding vector")
    
    # Processing metadata
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")
    request_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        },
        "json_schema_extra": {
            "example": {
                "success": True,
                "question_id": "q1",
                "question_text": "What are the benefits of using microservices architecture?",
                "answer_text": "Microservices architecture offers several key benefits...",
                "similar_blogs": [
                    {
                        "blog_id": "microservices_best_practices_abc123",
                        "title": "Microservices Best Practices for Enterprise Applications",
                        "url": "https://dev.to/author/microservices-best-practices",
                        "similarity_score": 0.87,
                        "summary_snippet": "This article explores advanced microservices patterns...",
                        "author": "John Developer",
                        "word_count": 2500,
                        "source_domain": "dev.to"
                    }
                ],
                "total_found": 3,
                "search_embedding_size": 1536,
                "processing_time_ms": 450.2
            }
        }
    }
