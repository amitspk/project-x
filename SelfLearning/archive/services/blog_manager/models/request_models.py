"""
Request models for the blog manager microservice.

Pydantic models for validating incoming API requests.
"""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, validator
from urllib.parse import urlparse


class BlogUrlRequest(BaseModel):
    """Request model for blog URL lookup."""
    
    url: HttpUrl = Field(
        ...,
        description="The blog URL to lookup",
        example="https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
    )
    
    include_summary: bool = Field(
        default=False,
        description="Whether to include blog summary in response"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Whether to include question metadata"
    )
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format and supported domains."""
        url_str = str(v)
        parsed = urlparse(url_str)
        
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        
        # Optional: Add domain whitelist validation
        # supported_domains = ['medium.com', 'dev.to', 'hashnode.com', 'baeldung.com']
        # if not any(domain in parsed.netloc for domain in supported_domains):
        #     raise ValueError(f"Unsupported domain: {parsed.netloc}")
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
                "include_summary": False,
                "include_metadata": True
            }
        }
    }


class BlogLookupRequest(BaseModel):
    """Request model for flexible blog lookup."""
    
    url: Optional[HttpUrl] = Field(
        default=None,
        description="The blog URL to lookup"
    )
    
    title: Optional[str] = Field(
        default=None,
        description="The blog title to lookup",
        min_length=3,
        max_length=500
    )
    
    blog_id: Optional[str] = Field(
        default=None,
        description="The internal blog ID",
        min_length=3,
        max_length=100
    )
    
    include_summary: bool = Field(
        default=False,
        description="Whether to include blog summary in response"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Whether to include question metadata"
    )
    
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of questions to return"
    )
    
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of questions to skip (for pagination)"
    )
    
    @validator('title')
    def validate_title(cls, v):
        """Validate title format."""
        if v and len(v.strip()) < 3:
            raise ValueError("Title must be at least 3 characters long")
        return v.strip() if v else v
    
    @validator('blog_id')
    def validate_blog_id(cls, v):
        """Validate blog_id format."""
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Blog ID must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    def __init__(self, **data):
        super().__init__(**data)
        # Ensure at least one identifier is provided
        if not any([self.url, self.title, self.blog_id]):
            raise ValueError("At least one of url, title, or blog_id must be provided")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
                "include_summary": False,
                "include_metadata": True,
                "limit": 10,
                "offset": 0
            }
        }
    }


class QuestionAnswerRequest(BaseModel):
    """Request model for general Q&A endpoint."""
    
    question: str = Field(
        ...,
        description="The question to ask the AI",
        min_length=5,
        max_length=1000,
        example="What are the benefits of using microservices architecture?"
    )
    
    @validator('question')
    def validate_question(cls, v):
        """Validate question format."""
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Question must be at least 5 characters long")
        if not v.endswith('?') and not any(word in v.lower() for word in ['what', 'how', 'why', 'when', 'where', 'which', 'who']):
            # Add question mark if it looks like a question but doesn't have one
            if any(word in v.lower() for word in ['explain', 'describe', 'tell me']):
                v += '?'
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "What are the benefits of using microservices architecture?"
            }
        }
    }


class SimilarBlogsRequest(BaseModel):
    """Request model for finding similar blogs by question ID."""
    
    question_id: str = Field(
        ...,
        description="The question ID to find similar blogs for",
        min_length=1,
        max_length=100,
        example="q1"
    )
    
    blog_url: Optional[HttpUrl] = Field(
        default=None,
        description="Optional blog URL to exclude from results (current blog)",
        example="https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
    )
    
    limit: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of similar blogs to return"
    )
    
    @validator('question_id')
    def validate_question_id(cls, v):
        """Validate question ID format."""
        v = v.strip()
        if not v:
            raise ValueError("Question ID cannot be empty")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question_id": "q1",
                "blog_url": "https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a",
                "limit": 3
            }
        }
    }
