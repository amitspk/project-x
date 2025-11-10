"""
Publisher configuration models.

This module defines the Publisher entity and its configuration schema
for multi-tenant blog processing.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, field_serializer
from enum import Enum
from fyi_widget_shared_library.services.llm_providers.model_config import LLMModelConfig

class LLMModel(str, Enum):
    """Supported LLM models."""
    GPT4O_MINI = "gpt-4o-mini"
    GPT4O = "gpt-4o"
    GPT35_TURBO = "gpt-3.5-turbo"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_HAIKU = "claude-3-5-haiku-20241022"
    GEMINI_15_PRO = "gemini-1.5-pro"
    GEMINI_15_FLASH = "gemini-1.5-flash"
    GEMINI_15_PRO_001 = "gemini-1.5-pro-001"
    GEMINI_15_FLASH_001 = "gemini-1.5-flash-001"
    GEMINI_10_PRO = "gemini-1.0-pro"
    GEMINI_10_PRO_VISION = "gemini-1.0-pro-vision"
    GEMINI_25_PRO = "gemini-2.5-pro"


# Helper function to get default model enum (defined after LLMModel to avoid NameError)
def _get_default_model_enum():
    """Get the LLMModel enum that corresponds to DEFAULT_MODEL from model_config."""
    from fyi_widget_shared_library.services.llm_providers.model_config import LLMModelConfig
    
    # Map DEFAULT_MODEL string to enum value
    default_model_str = LLMModelConfig.DEFAULT_MODEL
    for model_enum in LLMModel:
        if model_enum.value == default_model_str:
            return model_enum
    
    # Fallback if DEFAULT_MODEL doesn't match any enum (shouldn't happen)
    return LLMModel.GEMINI_25_PRO


# Helper function to get default temperature from model_config
def _get_default_temperature():
    """Get the default temperature from model_config."""
    from fyi_widget_shared_library.services.llm_providers.model_config import LLMModelConfig
    return LLMModelConfig.DEFAULT_TEMPERATURE


# Helper functions to get default max_tokens from model_config
def _get_default_max_tokens_summary():
    """Get the default max_tokens for summary from model_config."""
    from fyi_widget_shared_library.services.llm_providers.model_config import LLMModelConfig
    return LLMModelConfig.DEFAULT_MAX_TOKENS_SUMMARY


def _get_default_max_tokens_questions():
    """Get the default max_tokens for questions from model_config."""
    from fyi_widget_shared_library.services.llm_providers.model_config import LLMModelConfig
    return LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS


def _get_default_max_tokens_chat():
    """Get the default max_tokens for chat from model_config."""
    from fyi_widget_shared_library.services.llm_providers.model_config import LLMModelConfig
    return LLMModelConfig.DEFAULT_MAX_TOKENS_CHAT


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
    
    # LLM settings - Per-operation model configuration
    # Each operation type can use a different model
    
    summary_model: LLMModel = Field(
        default_factory=lambda: _get_default_model_enum(),
        description="LLM model to use for summary generation (defaults to DEFAULT_MODEL from model_config)"
    )
    questions_model: LLMModel = Field(
        default_factory=lambda: _get_default_model_enum(),
        description="LLM model to use for question-answer generation (defaults to DEFAULT_MODEL from model_config)"
    )
    chat_model: LLMModel = Field(
        default_factory=lambda: _get_default_model_enum(),
        description="LLM model to use for chat/question answering API (defaults to DEFAULT_MODEL from model_config)"
    )
    
    # Per-operation temperature settings (defaults from model_config)
    summary_temperature: float = Field(
        default_factory=_get_default_temperature,
        ge=0.0,
        le=1.0,
        description="Temperature for summary generation (defaults to DEFAULT_TEMPERATURE from model_config)"
    )
    questions_temperature: float = Field(
        default_factory=_get_default_temperature,
        ge=0.0,
        le=1.0,
        description="Temperature for question-answer generation (defaults to DEFAULT_TEMPERATURE from model_config)"
    )
    chat_temperature: float = Field(
        default_factory=_get_default_temperature,
        ge=0.0,
        le=1.0,
        description="Temperature for chat/question answering API (defaults to DEFAULT_TEMPERATURE from model_config)"
    )
    
    # Per-operation max_tokens settings (defaults from model_config)
    summary_max_tokens: int = Field(
        default_factory=_get_default_max_tokens_summary,
        ge=100,
        le=LLMModelConfig.DEFAULT_MAX_TOKENS_SUMMARY,
        description="Maximum tokens for summary generation (defaults to DEFAULT_MAX_TOKENS_SUMMARY from model_config)"
    )
    questions_max_tokens: int = Field(
        default_factory=_get_default_max_tokens_questions,
        ge=100,
        le=LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS,
        description="Maximum tokens for question-answer generation (defaults to DEFAULT_MAX_TOKENS_QUESTIONS from model_config)"
    )
    chat_max_tokens: int = Field(
        default_factory=_get_default_max_tokens_chat,
        ge=100,
        le=LLMModelConfig.DEFAULT_MAX_TOKENS_CHAT,
        description="Maximum tokens for chat/question answering API (defaults to DEFAULT_MAX_TOKENS_CHAT from model_config)"
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

    # Global usage limits
    max_total_blogs: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum total number of blogs that can be processed for this publisher (None for unlimited)"
    )

    # URL restrictions
    whitelisted_blog_urls: Optional[List[str]] = Field(
        default=None,
        description="List of allowed blog URLs or prefixes. Use '*' or leave empty to allow all."
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

    @validator('whitelisted_blog_urls', pre=True)
    def _normalize_whitelisted_urls(cls, value):
        """Normalize whitelist entries to a clean list or None."""
        if value in (None, "", [], ()):  # allow empty
            return None

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            # Attempt to parse JSON array; fall back to comma separated
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    value = parsed
                else:
                    value = [value]
            except (json.JSONDecodeError, TypeError):
                value = [part.strip() for part in value.split(',') if part.strip()]

        if isinstance(value, (set, tuple)):
            value = list(value)

        if isinstance(value, list):
            cleaned: List[str] = []
            for item in value:
                if item is None:
                    continue
                entry = str(item).strip()
                if entry:
                    cleaned.append(entry)
            return cleaned or None

        raise ValueError("whitelisted_blog_urls must be a list of strings")


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
    blog_slots_reserved: int = Field(default=0, ge=0)
    
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

