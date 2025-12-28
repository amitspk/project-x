"""Service layer for blog processing operations - uses orchestrator pattern."""

import logging
from typing import TYPE_CHECKING, Optional

from fyi_widget_worker_service.repositories import JobRepository, PublisherRepository
from fyi_widget_worker_service.models.job_models import ProcessingJob

if TYPE_CHECKING:
    from fyi_widget_worker_service.services.blog_content_repository import BlogContentRepository

from .content_retrieval_service import ContentRetrievalService
from .threshold_service import ThresholdService
from .llm_generation_service import LLMGenerationService
from .blog_processing_orchestrator import BlogProcessingOrchestrator

logger = logging.getLogger(__name__)


class BlogProcessingService:
    """
    Service for processing blog jobs.
    
    This is now a thin wrapper that delegates to BlogProcessingOrchestrator,
    which coordinates specialized services following SRP.
    """
    
    def __init__(
        self,
        job_repo: JobRepository,
        publisher_repo: PublisherRepository,
        storage: "BlogContentRepository",
        content_retrieval_service: ContentRetrievalService,
        threshold_service: ThresholdService,
        llm_generation_service: LLMGenerationService,
        orchestrator: Optional[BlogProcessingOrchestrator] = None,
    ):
        """
        Initialize service with dependencies.
        
        All services are injected via constructor for better testability and pure DI.
        
        Args:
            job_repo: Job repository
            publisher_repo: Publisher repository
            storage: Storage service (needed by orchestrator)
            content_retrieval_service: Content retrieval service
            threshold_service: Threshold checking service
            llm_generation_service: LLM generation service
            orchestrator: Optional orchestrator (will be created if not provided)
                         If provided, this allows full mocking in tests
        """
        # Use provided orchestrator or create one with injected services
        if orchestrator is not None:
            self.orchestrator = orchestrator
        else:
            # Create orchestrator with injected services (pure DI)
            self.orchestrator = BlogProcessingOrchestrator(
                job_repo=job_repo,
                publisher_repo=publisher_repo,
                storage=storage,
                content_retrieval_service=content_retrieval_service,
                threshold_service=threshold_service,
                llm_generation_service=llm_generation_service
            )
    
    async def process_job(self, job: ProcessingJob) -> None:
        """
        Process a single job by delegating to the orchestrator.
        
        Args:
            job: Job to process
        """
        await self.orchestrator.process_job(job)
