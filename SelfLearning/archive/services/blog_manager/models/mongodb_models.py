"""
MongoDB document models for the blog manager microservice.

Defines the structure of documents stored in MongoDB collections.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic models."""
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.to_string_ser_schema(),
        )
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")


class BlogDocument(BaseModel):
    """MongoDB document model for raw blog content."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    blog_id: str = Field(..., description="Internal blog identifier")
    url: str = Field(..., description="Blog URL")
    title: str = Field(..., description="Blog title")
    content: str = Field(..., description="Full blog content")
    html_content: Optional[str] = Field(default="", description="HTML content")
    author: Optional[str] = Field(default="", description="Blog author")
    published_date: Optional[datetime] = Field(default=None, description="Publication date")
    crawled_at: datetime = Field(..., description="When content was crawled")
    source_domain: str = Field(..., description="Source domain")
    word_count: int = Field(..., description="Word count")
    language: str = Field(default="en", description="Content language")
    content_type: str = Field(default="article", description="Content type")
    raw_metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw metadata")
    processing_status: str = Field(default="pending", description="Processing status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class SummaryDocument(BaseModel):
    """MongoDB document model for blog summaries."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    blog_id: str = Field(..., description="Internal blog identifier")
    summary_text: str = Field(..., description="Summary text")
    key_points: List[str] = Field(default_factory=list, description="Key points")
    main_topics: List[str] = Field(default_factory=list, description="Main topics")
    summary_length: str = Field(default="medium", description="Summary length")
    summary_type: str = Field(default="abstractive", description="Summary type")
    ai_model: str = Field(default="gpt-4", description="AI model used")
    ai_provider: str = Field(default="openai", description="AI provider")
    generation_parameters: Dict[str, Any] = Field(default_factory=dict, description="Generation parameters")
    confidence_score: float = Field(default=0.0, description="Confidence score")
    coherence_score: Optional[float] = Field(default=None, description="Coherence score")
    relevance_score: Optional[float] = Field(default=None, description="Relevance score")
    
    # Embedding fields
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding")
    embedding_model: Optional[str] = Field(default=None, description="Embedding model")
    embedding_provider: Optional[str] = Field(default=None, description="Embedding provider")
    embedding_dimensions: int = Field(default=0, description="Embedding dimensions")
    embedding_generated_at: Optional[datetime] = Field(default=None, description="Embedding generation timestamp")
    
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")
    processing_time_seconds: Optional[float] = Field(default=None, description="Processing time")
    tokens_used: Optional[float] = Field(default=None, description="Tokens used")
    cost_usd: Optional[float] = Field(default=None, description="Cost in USD")
    version: int = Field(default=1, description="Version number")
    is_active: bool = Field(default=True, description="Is active")
    
    user_ratings: Dict[str, Any] = Field(default_factory=dict, description="User ratings")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class QuestionDocument(BaseModel):
    """MongoDB document model for blog questions."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    blog_id: str = Field(..., description="Internal blog identifier")
    question: str = Field(..., description="Question text")
    answer: str = Field(..., description="Answer text")
    question_type: str = Field(..., description="Question type")
    difficulty_level: str = Field(default="intermediate", description="Difficulty level")
    topic_area: str = Field(default="general", description="Topic area")
    
    # AI generation metadata
    ai_model: str = Field(default="gpt-4", description="AI model used")
    ai_provider: str = Field(default="openai", description="AI provider")
    generation_parameters: Dict[str, Any] = Field(default_factory=dict, description="Generation parameters")
    
    # Quality scores
    question_quality_score: float = Field(default=0.0, description="Question quality score")
    answer_accuracy_score: Optional[float] = Field(default=None, description="Answer accuracy score")
    relevance_score: Optional[float] = Field(default=None, description="Relevance score")
    
    # Learning metadata
    learning_objective: Optional[str] = Field(default=None, description="Learning objective")
    bloom_taxonomy_level: str = Field(default="comprehension", description="Bloom's taxonomy level")
    
    # Question set metadata
    question_set_id: str = Field(..., description="Question set identifier")
    question_order: int = Field(..., description="Question order in set")
    total_questions_in_set: int = Field(..., description="Total questions in set")
    
    # Usage statistics
    times_asked: int = Field(default=0, description="Times asked")
    correct_answers: int = Field(default=0, description="Correct answers")
    user_feedback: Dict[str, Any] = Field(default_factory=dict, description="User feedback")
    
    # Processing metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")
    processing_time_seconds: Optional[float] = Field(default=None, description="Processing time")
    tokens_used: Optional[float] = Field(default=None, description="Tokens used")
    
    # Status and review
    is_active: bool = Field(default=True, description="Is active")
    review_status: str = Field(default="approved", description="Review status")
    reviewed_by: Optional[str] = Field(default=None, description="Reviewed by")
    reviewed_at: Optional[datetime] = Field(default=None, description="Review timestamp")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }
