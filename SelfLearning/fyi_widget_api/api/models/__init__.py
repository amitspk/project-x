"""API-specific models (response formatting and Swagger documentation)."""

from .response_models import (
    StandardResponse,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    ResponseMetadata,
)

from .job_models import JobStatus, JobResult, JobCreateRequest, JobStatusResponse

from .publisher_models import (
    Publisher,
    PublisherConfig,
    LLMModel,
    PublisherStatus,
    PublisherCreateRequest,
    PublisherUpdateRequest,
)

from .schema_models import (
    # Request models
    ProcessBlogRequest,
    GetQuestionsRequest,
    SearchSimilarRequest,
    # Data structure models
    QuestionAnswerPair,
    BlogSummary,
    SimilarBlog,
    BlogContentResponse,
    # Response models
    SearchSimilarResponse,
    HealthCheckResponse,
    ProcessingResult,
)

from .swagger_models import (
    StandardSuccessResponse,
    StandardErrorResponse,
    # Questions
    QuestionsByUrlResponse,
    QuestionByIdResponse,
    CheckAndLoadResponse,
    # Jobs
    ProcessJobResponse,
    JobStatusResponse,
    JobStatsResponse,
    # QA
    QAResponse,
    # Search
    SearchResponse,
    # Publishers
    PublisherOnboardResponse,
    PublisherGetResponse,
    PublishersListResponse,
    PublisherUpdateResponse,
    PublisherDeleteResponse,
    PublisherConfigResponse,
    PublisherRegenerateApiKeyResponse,
    PublisherMetadataResponse,
)

__all__ = [
    # Response models
    "StandardResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
    "ResponseMetadata",
    # Job models
    "JobStatus",
    "JobResult",
    "JobCreateRequest",
    "JobStatusResponse",
    # Publisher models
    "Publisher",
    "PublisherConfig",
    "LLMModel",
    "PublisherStatus",
    "PublisherCreateRequest",
    "PublisherUpdateRequest",
    # Schema models
    "ProcessBlogRequest",
    "GetQuestionsRequest",
    "SearchSimilarRequest",
    "QuestionAnswerPair",
    "BlogSummary",
    "SimilarBlog",
    "BlogContentResponse",
    "SearchSimilarResponse",
    "HealthCheckResponse",
    "ProcessingResult",
    # Swagger models
    "StandardSuccessResponse",
    "StandardErrorResponse",
    "QuestionsByUrlResponse",
    "QuestionByIdResponse",
    "CheckAndLoadResponse",
    "ProcessJobResponse",
    "JobStatusResponse",
    "JobStatsResponse",
    "QAResponse",
    "SearchResponse",
    "PublisherOnboardResponse",
    "PublisherGetResponse",
    "PublishersListResponse",
    "PublisherUpdateResponse",
    "PublisherDeleteResponse",
    "PublisherConfigResponse",
    "PublisherRegenerateApiKeyResponse",
    "PublisherMetadataResponse",
]

