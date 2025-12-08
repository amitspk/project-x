"""Shared models."""

from .job_queue import ProcessingJob, JobStatus, JobResult, JobCreateRequest, JobStatusResponse
from .api_response import (
    StandardResponse,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    ResponseMetadata
)

# Import Swagger response models
from .swagger_responses import (
    StandardSuccessResponse,
    StandardErrorResponse,
    # Questions
    QuestionsByUrlResponse,
    QuestionByIdResponse,
    CheckAndLoadResponse,
    # Jobs
    ProcessJobResponse,
    JobStatusResponse as SwaggerJobStatusResponse,
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

# Import schemas if they exist
try:
    from .schemas import *
except ImportError:
    pass

__all__ = [
    "ProcessingJob",
    "JobStatus",
    "JobResult",
    "JobCreateRequest",
    "JobStatusResponse",
    "StandardResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
    "ResponseMetadata",
    # Swagger responses
    "StandardSuccessResponse",
    "StandardErrorResponse",
    "QuestionsByUrlResponse",
    "QuestionByIdResponse",
    "CheckAndLoadResponse",
    "ProcessJobResponse",
    "SwaggerJobStatusResponse",
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
