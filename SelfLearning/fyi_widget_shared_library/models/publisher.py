"""
Publisher configuration models.

This module defines the Publisher entity and its configuration schema
for multi-tenant blog processing.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator, field_serializer
from enum import Enum


class LLMModel(str, Enum):
    """Supported LLM models."""
    GPT4O_MINI = "gpt-4o-mini"
    GPT4O = "gpt-4o"
    GPT35_TURBO = "gpt-3.5-turbo"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_HAIKU = "claude-3-5-haiku-20241022"


class PublisherStatus(str, Enum):
    """Publisher account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class PublisherConfig(BaseModel):
    """Configuration for a publisher's content processing."""
    
    # Question generation settings
    questions_per_blog: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of Q&A pairs to generate per blog"
    )
    
    # LLM settings
    llm_model: LLMModel = Field(
        default=LLMModel.GPT4O_MINI,
        description="LLM model to use for generation"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="LLM temperature for generation"
    )
    max_tokens: int = Field(
        default=2000,
        ge=100,
        le=4000,
        description="Maximum tokens per LLM request"
    )
    
    # Content processing settings
    generate_summary: bool = Field(
        default=True,
        description="Whether to generate blog summaries"
    )
    generate_embeddings: bool = Field(
        default=True,
        description="Whether to generate embeddings for search"
    )
    
    # Rate limiting
    daily_blog_limit: Optional[int] = Field(
        default=100,
        ge=1,
        description="Maximum blogs to process per day (None for unlimited)"
    )
    
    # Custom prompts (optional) - Three-Layer Architecture
    # Layer 1 (System): Role + format enforcement (non-negotiable, handled by LLMService)
    # Layer 2 (Instructions): Custom content style/focus - THIS IS WHAT YOU CUSTOMIZE
    # Layer 3 (Format): JSON schema enforcement (non-negotiable, handled by LLMService)
    
    custom_question_prompt: Optional[str] = Field(
        default=None,
        description="""Custom instructions for question generation style/focus.
        
        These instructions guide the CONTENT and STYLE of questions, NOT the format.
        The JSON output format is enforced by the system and cannot be changed.
        
        Example for Technical Blog:
        'Generate technical question-answer pairs that focus on code examples and 
        implementation details. Include how-to practical questions and emphasize 
        best practices. Use technical terminology appropriate for developers.'
        
        Example for Marketing Blog:
        'Generate engaging question-answer pairs that focus on actionable insights 
        and strategies. Include real-world examples and case studies. Use 
        conversational, accessible language and emphasize ROI and business impact.'
        
        If not provided, uses default educational Q&A instructions.
        """
    )
    custom_summary_prompt: Optional[str] = Field(
        default=None,
        description="""Custom instructions for summary generation style/focus.
        
        These instructions guide the CONTENT and STYLE of summaries, NOT the format.
        The JSON output format is enforced by the system and cannot be changed.
        
        Example for Technical Blog:
        'Create a technical summary highlighting key technologies, frameworks, and 
        implementation approaches. Focus on practical takeaways for developers and 
        emphasize code patterns or architectural decisions.'
        
        Example for Business Blog:
        'Create a business-focused summary emphasizing strategic insights, ROI 
        implications, and actionable recommendations. Use executive-level language 
        and focus on impact and outcomes.'
        
        If not provided, uses default summary instructions.
        """
    )
    
    # UI customization
    ui_theme_color: Optional[str] = Field(
        default="#6366f1",
        description="Primary color for question cards"
    )
    ui_icon_style: Optional[str] = Field(
        default="emoji",
        description="Icon style: emoji, material, fontawesome"
    )
    
    class Config:
        """Pydantic config."""
        use_enum_values = True


class Publisher(BaseModel):
    """Publisher entity."""
    
    id: Optional[str] = Field(default=None, description="Publisher ID (UUID)")
    name: str = Field(..., min_length=1, max_length=255, description="Publisher name")
    domain: str = Field(..., description="Publisher's primary domain (e.g., example.com)")
    email: str = Field(..., description="Contact email")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    
    status: PublisherStatus = Field(default=PublisherStatus.TRIAL)
    
    # Configuration
    config: PublisherConfig = Field(default_factory=PublisherConfig)
    
    # Metadata
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    last_active_at: Optional[datetime] = Field(default=None)
    
    # Usage tracking
    total_blogs_processed: int = Field(default=0, ge=0)
    total_questions_generated: int = Field(default=0, ge=0)
    
    # Billing (optional)
    subscription_tier: Optional[str] = Field(
        default="free",
        description="Subscription tier: free, basic, pro, enterprise"
    )
    
    @validator('domain')
    def normalize_domain(cls, v):
        """Normalize domain to lowercase without protocol."""
        v = v.lower().strip()
        # Remove protocol if present
        for prefix in ['https://', 'http://', 'www.']:
            if v.startswith(prefix):
                v = v[len(prefix):]
        # Remove trailing slash
        return v.rstrip('/')
    
    @validator('email')
    def validate_email(cls, v):
        """Basic email validation."""
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_serializer('created_at', 'updated_at', 'last_active_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """Serialize datetime fields to ISO format strings."""
        if dt is None:
            return None
        return dt.isoformat()
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PublisherCreateRequest(BaseModel):
    """Request model for creating a new publisher."""
    name: str = Field(..., min_length=1, max_length=255)
    domain: str
    email: str
    config: Optional[PublisherConfig] = Field(default_factory=PublisherConfig)
    subscription_tier: Optional[str] = Field(default="free")


class PublisherUpdateRequest(BaseModel):
    """Request model for updating a publisher."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = None
    status: Optional[PublisherStatus] = None
    config: Optional[PublisherConfig] = None
    subscription_tier: Optional[str] = None


class PublisherResponse(BaseModel):
    """Response model for publisher endpoints."""
    success: bool
    publisher: Optional[Publisher] = None
    message: Optional[str] = None
    api_key: Optional[str] = Field(
        default=None,
        description="API key (only returned on creation)"
    )


class PublisherListResponse(BaseModel):
    """Response model for listing publishers."""
    success: bool
    publishers: list[Publisher]
    total: int
    page: int
    page_size: int

