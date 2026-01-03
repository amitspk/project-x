"""API-specific models (response formatting and Swagger documentation)."""

from .response_models import (
    StandardResponse,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    ResponseMetadata,
)


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
    SearchSimilarRequest,
    # Data structure models
    QuestionAnswerPair,
    BlogSummary,
    SimilarBlog,
    # Response models
    SearchSimilarResponse,
)

from .swagger_models import (
    StandardSuccessResponse,
    StandardErrorResponse,
    # Questions
    QuestionByIdResponse,
    CheckAndLoadResponse,
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

from .blog_processing_models import (
    # Enums
    BlogProcessingStatus,
    # Queue models
    BlogProcessingQueueEntry,
    BlogProcessingQueueStats,
)

__all__ = [
    # Response models
    "StandardResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
    "ResponseMetadata",
    # Publisher models
    "Publisher",
    "PublisherConfig",
    "LLMModel",
    "PublisherStatus",
    "PublisherCreateRequest",
    "PublisherUpdateRequest",
    # Schema models
    "SearchSimilarRequest",
    "QuestionAnswerPair",
    "BlogSummary",
    "SimilarBlog",
    "SearchSimilarResponse",
    # Swagger models
    "StandardSuccessResponse",
    "StandardErrorResponse",
    "QuestionByIdResponse",
    "CheckAndLoadResponse",
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
    # Blog processing models
    "BlogProcessingStatus",
    "BlogProcessingQueueEntry",
    "BlogProcessingQueueStats",
]

