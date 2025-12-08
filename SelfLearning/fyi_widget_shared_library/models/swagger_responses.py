"""
Swagger/OpenAPI response models for API documentation.

These models are used to generate accurate API documentation
with proper response schemas for UI developers.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from fyi_widget_shared_library.services.llm_providers.model_config import LLMModelConfig


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
# Questions Router Response Models
# ============================================================================

class QuestionListSchema(BaseModel):
    """Question schema for list endpoints (without created_at)."""
    id: str = Field(..., example="68f216e74c1c51f257077318")
    question: str = Field(..., example="What is the main topic of this article?")
    answer: str = Field(..., example="The article discusses...")


class QuestionSchema(BaseModel):
    """Question schema for single question endpoint (includes created_at)."""
    id: str = Field(..., example="68f216e74c1c51f257077318")
    question: str = Field(..., example="What is the main topic of this article?")
    answer: str = Field(..., example="The article discusses...")
    created_at: Optional[str] = Field(None, example="2025-10-18T14:30:00", description="Created timestamp")


class BlogInfoSchema(BaseModel):
    """Blog info schema."""
    id: str = Field(..., example="68f216e74c1c51f257077316")
    title: str = Field(..., example="Article Title")
    url: str = Field(..., example="https://example.com/article")
    author: str = Field(..., example="John Doe")
    published_date: str = Field(..., example="2025-10-18")
    question_count: int = Field(..., example=10)


class QuestionsByUrlResult(BaseModel):
    """Result for questions by URL endpoint."""
    questions: List[QuestionListSchema]
    blog_info: BlogInfoSchema


class QuestionsByUrlResponse(StandardSuccessResponse):
    """Response for GET /questions/by-url."""
    result: QuestionsByUrlResult


class QuestionByIdResponse(StandardSuccessResponse):
    """Response for GET /questions/{question_id}."""
    result: QuestionSchema


class CheckAndLoadResult(BaseModel):
    """Result for check-and-load endpoint."""
    processing_status: str = Field(..., example="ready", description="Status: ready, processing, not_started, or failed")
    blog_url: str = Field(..., example="https://example.com/article")
    questions: Optional[List[QuestionListSchema]] = Field(None, description="Questions if ready, None otherwise")
    blog_info: Optional[BlogInfoSchema] = Field(None, description="Blog info if ready, None otherwise")
    job_id: Optional[str] = Field(None, example="72815d48-7283-4a89-9004-3465d1b4c293", description="Job ID if processing or not_started")
    message: str = Field(..., example="Questions ready - loaded from cache")


class CheckAndLoadResponse(StandardSuccessResponse):
    """Response for GET /questions/check-and-load."""
    result: CheckAndLoadResult


# ============================================================================
# Jobs Router Response Models
# ============================================================================

class JobResultSchema(BaseModel):
    """Job result schema."""
    job_id: str = Field(..., example="72815d48-7283-4a89-9004-3465d1b4c293")
    blog_url: str = Field(..., example="https://example.com/article")
    status: str = Field(..., example="COMPLETED")


class ProcessJobResponse(StandardSuccessResponse):
    """Response for POST /jobs/process."""
    status_code: int = Field(202, example=202)
    result: JobResultSchema


class JobStatusSchema(BaseModel):
    """Job status schema."""
    job_id: str = Field(..., example="72815d48-7283-4a89-9004-3465d1b4c293")
    blog_url: str = Field(..., example="https://example.com/article")
    status: str = Field(..., example="completed")
    failure_count: int = Field(..., example=0)
    error_message: Optional[str] = Field(None, example=None)
    created_at: str = Field(..., example="2025-10-18T14:30:00")
    started_at: Optional[str] = Field(None, example="2025-10-18T14:30:05")
    completed_at: Optional[str] = Field(None, example="2025-10-18T14:35:00")
    processing_time_seconds: Optional[float] = Field(None, example=295.5)
    result: Optional[Dict[str, Any]] = Field(None, example={"summary_id": "abc123", "question_count": 5})
    updated_at: Optional[str] = Field(None, example="2025-10-18T14:35:00")


class JobStatusResponse(StandardSuccessResponse):
    """Response for GET /jobs/status/{job_id}."""
    result: JobStatusSchema


class QueueStatsSchema(BaseModel):
    """Queue statistics schema."""
    queued: int = Field(..., example=5)
    processing: int = Field(..., example=2)
    completed: int = Field(..., example=100)
    failed: int = Field(..., example=3)
    cancelled: int = Field(..., example=1)


class JobStatsResult(BaseModel):
    """Job stats result schema."""
    queue_stats: QueueStatsSchema
    total_jobs: int = Field(..., example=111)


class JobStatsResponse(StandardSuccessResponse):
    """Response for GET /jobs/stats."""
    result: JobStatsResult


# ============================================================================
# QA Router Response Models
# ============================================================================

class QAResultSchema(BaseModel):
    """Q&A result schema."""
    success: bool = Field(..., example=True)
    question: str = Field(..., example="What is AI?")
    answer: str = Field(..., example="Artificial Intelligence refers to...")
    word_count: int = Field(..., example=150)
    processing_time_ms: float = Field(..., example=1234.56)


class QAResponse(StandardSuccessResponse):
    """Response for POST /qa/ask."""
    result: QAResultSchema


# ============================================================================
# Search Router Response Models
# ============================================================================

class SimilarBlogSchema(BaseModel):
    """Similar blog schema."""
    blog_id: str = Field(..., example="68f216e74c1c51f257077316")
    title: str = Field(..., example="Similar Article")
    url: str = Field(..., example="https://example.com/similar")
    similarity_score: float = Field(..., example=0.85)


class SearchResultSchema(BaseModel):
    """Search result schema."""
    similar_blogs: List[SimilarBlogSchema]
    total: int = Field(..., example=5)


class SearchResponse(StandardSuccessResponse):
    """Response for POST /search/similar."""
    result: SearchResultSchema


# ============================================================================
# Publishers Router Response Models
# ============================================================================

class PublisherConfigSchema(BaseModel):
    """Publisher configuration schema."""
    questions_per_blog: int = Field(..., example=5)
    summary_model: str = Field(..., example="gpt-4o-mini")
    questions_model: str = Field(..., example="gpt-4o-mini")
    chat_model: str = Field(..., example="gpt-4o-mini")
    # Temperature fields are always excluded from GET responses
    summary_max_tokens: int = Field(..., example=LLMModelConfig.DEFAULT_MAX_TOKENS_SUMMARY)
    questions_max_tokens: int = Field(..., example=LLMModelConfig.DEFAULT_MAX_TOKENS_QUESTIONS)
    chat_max_tokens: int = Field(..., example=LLMModelConfig.DEFAULT_MAX_TOKENS_CHAT)
    # generate_summary and generate_embeddings are always excluded from GET responses
    use_grounding: bool = Field(False, example=False, description="Enable Google Search grounding for question generation during blog processing (Gemini models only). When enabled, provides real-time information and citations. Note: Grounding is NOT used in the Q&A /ask endpoint to control costs.")
    daily_blog_limit: int = Field(..., example=100)
    max_total_blogs: int | None = Field(None, example=500, description="Maximum total blogs allowed (null for unlimited)")
    threshold_before_processing_blog: int = Field(0, example=0, description="Threshold value before processing a blog. Defaults to 0 when publisher is onboarded.")
    whitelisted_blog_urls: List[str] | None = Field(None, example=["https://example.com/blog/","/news/"], description="Allowed blog URL prefixes. Use '*' or null to allow all.")
    # Widget configuration (stored in config.widget in database)
    widget: Optional[Dict[str, Any]] = Field(None, example={
        "useDummyData": False,
        "theme": "light",
        "currentStructure": "",
        "gaTrackingId": "G-WPWFCMCSS3",
        "gaEnabled": True,
        "adsenseForSearch": None,
        "adsenseDisplay": None,
        "googleAdManager": None
    }, description="Widget configuration including theme, GA settings, and ad configs")


class PublisherSchema(BaseModel):
    """Publisher schema."""
    id: str = Field(..., example="a1a02dfd-b877-4d9d-b072-6936b39fc737")
    name: str = Field(..., example="Tech Blog Inc")
    domain: str = Field(..., example="techblog.com")
    email: str = Field(..., example="admin@techblog.com")
    status: str = Field(..., example="active")
    config: PublisherConfigSchema
    created_at: str = Field(..., example="2025-10-18T14:30:00")
    subscription_tier: str = Field(..., example="free")


class PublisherOnboardResult(BaseModel):
    """Publisher onboard result schema."""
    success: bool = Field(..., example=True)
    publisher: PublisherSchema
    api_key: str = Field(..., example="pub_abc123def456")
    message: str = Field(..., example="Publisher onboarded successfully")


class PublisherOnboardResponse(StandardSuccessResponse):
    """Response for POST /publishers/onboard."""
    status_code: int = Field(201, example=201)
    result: PublisherOnboardResult


class PublisherGetResult(BaseModel):
    """Publisher get result schema."""
    success: bool = Field(..., example=True)
    publisher: PublisherSchema


class PublisherGetResponse(StandardSuccessResponse):
    """Response for GET /publishers/{publisher_id} and /publishers/by-domain/{domain}."""
    result: PublisherGetResult


class PublishersListResult(BaseModel):
    """Publishers list result schema."""
    success: bool = Field(..., example=True)
    publishers: List[PublisherSchema]
    total: int = Field(..., example=50)
    page: int = Field(..., example=1)
    page_size: int = Field(..., example=10)


class PublishersListResponse(StandardSuccessResponse):
    """Response for GET /publishers/."""
    result: PublishersListResult
    metadata: ResponseMetadataSchema


class PublisherUpdateResult(BaseModel):
    """Publisher update result schema."""
    success: bool = Field(..., example=True)
    publisher: PublisherSchema
    message: str = Field(..., example="Publisher updated successfully")


class PublisherUpdateResponse(StandardSuccessResponse):
    """Response for PUT /publishers/{publisher_id}."""
    result: PublisherUpdateResult


class PublisherDeleteResult(BaseModel):
    """Publisher delete result schema."""
    success: bool = Field(..., example=True)
    message: str = Field(..., example="Publisher deleted successfully")


class PublisherDeleteResponse(StandardSuccessResponse):
    """Response for DELETE /publishers/{publisher_id}."""
    result: PublisherDeleteResult


class PublisherConfigResult(BaseModel):
    """Publisher config result schema."""
    success: bool = Field(..., example=True)
    config: PublisherConfigSchema


class PublisherConfigResponse(StandardSuccessResponse):
    """Response for GET /publishers/{publisher_id}/config."""
    result: PublisherConfigResult


class PublisherRegenerateApiKeyResult(BaseModel):
    """Publisher regenerate API key result schema."""
    publisher: PublisherSchema
    api_key: str = Field(..., example="pub_NewGeneratedKey123...")
    message: str = Field(..., example="API key regenerated successfully. Please save this key - it won't be shown again.")


class PublisherRegenerateApiKeyResponse(StandardSuccessResponse):
    """Response for POST /publishers/{publisher_id}/regenerate-api-key."""
    result: PublisherRegenerateApiKeyResult = Field(..., description="Details of the publisher and the new API key")
    message: str = "API key regenerated successfully"


# ============================================================================
# Publisher Metadata Response Models
# ============================================================================

class AdSenseForSearchConfig(BaseModel):
    """AdSense for Search configuration schema."""
    enabled: bool = Field(..., example=True)
    pubId: Optional[str] = Field(None, example="partner-pub-4082803764726235")
    styleId: Optional[str] = Field(None, example="7395764353")
    adtest: Optional[bool] = Field(None, example=False)
    numberOfAds: Optional[int] = Field(None, example=3)
    hl: Optional[str] = Field(None, example="en")
    channel: Optional[str] = Field(None, example="7374542267")
    defaultQuery: Optional[str] = Field(None, example="")
    querySource: Optional[str] = Field(None, example="question")
    containerSuffix: Optional[str] = Field(None, example="-search-ads")
    renderMode: Optional[str] = Field(None, example="iframe")
    width: Optional[str] = Field(None, example="auto")
    minHeight: Optional[int] = Field(None, example=100)
    linkTarget: Optional[str] = Field(None, example="_top")
    adsafe: Optional[str] = Field(None, example="low")
    resultsPageQueryParam: Optional[str] = Field(None, example="query")
    ignoredPageParams: Optional[List[str]] = Field(None, example=["utm_source", "utm_medium", "ref"])
    adUnitOptions: Optional[Dict[str, Any]] = Field(None, example={})


class AdSenseDisplayConfig(BaseModel):
    """AdSense Display Ads configuration schema."""
    enabled: bool = Field(..., example=True)
    pubId: Optional[str] = Field(None, example="ca-pub-123456789")
    slotId: Optional[str] = Field(None, example="1234567890")
    adFormat: Optional[str] = Field(None, example="auto")
    adtest: Optional[bool] = Field(None, example=False)
    useIsolation: Optional[bool] = Field(None, example=None)


class GoogleAdManagerConfig(BaseModel):
    """Google Ad Manager configuration schema."""
    enabled: bool = Field(..., example=True)
    adUnitPath: Optional[str] = Field(None, example="/12345678/example/display")
    sizes: Optional[List[List[int]]] = Field(None, example=[[300, 250], [728, 90]])
    targeting: Optional[Dict[str, Any]] = Field(None, example={"pos": "top"})
    channel: Optional[str] = Field(None, example="12345678")
    collapseEmpty: Optional[bool] = Field(None, example=True)
    responsive: Optional[bool] = Field(None, example=True)
    useIsolation: Optional[bool] = Field(None, example=None)


class PublisherMetadataResult(BaseModel):
    """Publisher metadata result schema."""
    domain: str = Field(..., example="example.com")
    publisher_id: str = Field(..., example="pub_123456")
    publisher_name: Optional[str] = Field(None, example="Example Blog Network")
    useDummyData: Optional[bool] = Field(None, example=False)
    theme: Optional[str] = Field(None, example="light")
    currentStructure: Optional[str] = Field(None, example="")
    gaTrackingId: Optional[str] = Field(None, example="G-WPWFCMCSS3")
    gaEnabled: Optional[bool] = Field(None, example=True)
    adsenseForSearch: Optional[AdSenseForSearchConfig] = None
    adsenseDisplay: Optional[AdSenseDisplayConfig] = None
    googleAdManager: Optional[GoogleAdManagerConfig] = None


class PublisherMetadataResponse(StandardSuccessResponse):
    """Response for GET /publishers/metadata."""
    result: PublisherMetadataResult

