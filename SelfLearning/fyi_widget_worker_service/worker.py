"""Worker service - polls for jobs and processes them."""

import asyncio
import logging
import os
import signal
import time
from typing import Optional, Callable, Coroutine, Any
from dotenv import load_dotenv

from fyi_widget_worker_service.core.database import DatabaseManager
from fyi_widget_worker_service.repositories import JobRepository, PublisherRepository
from fyi_widget_worker_service.models.job_models import ProcessingJob
from fyi_widget_worker_service.services.blog_crawler import BlogCrawler
from fyi_widget_worker_service.services.llm_content_generator import LLMContentGenerator
from fyi_widget_worker_service.services.blog_content_repository import BlogContentRepository
from fyi_widget_worker_service.utils import extract_domain

# Import configuration
from fyi_widget_worker_service.core.config import get_config, WorkerServiceConfig

# Import services
from fyi_widget_worker_service.services.blog_processing_service import BlogProcessingService
from fyi_widget_worker_service.services.content_retrieval_service import ContentRetrievalService
from fyi_widget_worker_service.services.threshold_service import ThresholdService
from fyi_widget_worker_service.services.llm_generation_service import LLMGenerationService

# Import metrics
from fyi_widget_worker_service.core.metrics import (
    job_queue_size,
    poll_iterations_total,
    poll_errors_total,
    worker_uptime_seconds,
    jobs_polled_total,
)
from fyi_widget_worker_service.core.metrics_server import start_metrics_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BlogProcessingWorker:
    """Worker that polls for jobs and processes blogs."""
    
    def __init__(
        self,
        config: WorkerServiceConfig,
        db_manager: DatabaseManager,
        crawler: BlogCrawler,
        # Factory functions for lifecycle-dependent dependencies (called after DB connection)
        publisher_repo_factory: Callable[[str], Coroutine[Any, Any, PublisherRepository]],
        job_repo_factory: Callable[[], JobRepository],  # Will receive database via closure
        storage_factory: Callable[[], BlogContentRepository],  # Will receive database via closure
        llm_service_factory: Callable[[], LLMContentGenerator],
        content_retrieval_service_factory: Callable[[BlogCrawler, BlogContentRepository], ContentRetrievalService],
        threshold_service_factory: Callable[[BlogContentRepository, JobRepository], ThresholdService],
        llm_generation_service_factory: Callable[[LLMContentGenerator], LLMGenerationService],
        blog_processing_service_factory: Callable[[JobRepository, PublisherRepository, BlogContentRepository, ContentRetrievalService, ThresholdService, LLMGenerationService], BlogProcessingService],
    ):
        """
        Initialize worker with configuration and dependencies.
        
        Pure Dependency Injection pattern - all dependencies are injected via constructor.
        Lifecycle-dependent dependencies (requiring DB connection) are injected as factory functions
        that will be called in start() after database connection is established.
        
        Args:
            config: Worker service configuration
            db_manager: DatabaseManager instance (required)
                       Must be injected - the worker manages its lifecycle (connect/disconnect)
                       but does not create it. This allows for better testability.
            crawler: BlogCrawler instance (required)
                    Must be injected for better testability - can be mocked in tests.
            publisher_repo_factory: Async factory function that takes postgres_url and returns PublisherRepository
            job_repo_factory: Factory function that takes no args (uses self.db_manager.database) and returns JobRepository
            storage_factory: Factory function that takes no args (uses self.db_manager.database) and returns BlogContentRepository
            llm_service_factory: Factory function that takes no args and returns LLMContentGenerator
            content_retrieval_service_factory: Factory function that creates ContentRetrievalService
            threshold_service_factory: Factory function that creates ThresholdService
            llm_generation_service_factory: Factory function that creates LLMGenerationService
            blog_processing_service_factory: Factory function that creates BlogProcessingService
        """
        self.config = config
        self.db_manager = db_manager
        self.crawler = crawler
        
        # Store factory functions
        self.publisher_repo_factory = publisher_repo_factory
        self.job_repo_factory = job_repo_factory
        self.storage_factory = storage_factory
        self.llm_service_factory = llm_service_factory
        self.content_retrieval_service_factory = content_retrieval_service_factory
        self.threshold_service_factory = threshold_service_factory
        self.llm_generation_service_factory = llm_generation_service_factory
        self.blog_processing_service_factory = blog_processing_service_factory
        
        # Dependencies (initialized in start() using factory functions)
        self.job_repo: Optional[JobRepository] = None
        self.publisher_repo: Optional[PublisherRepository] = None
        self.llm_service: Optional[LLMContentGenerator] = None
        self.storage: Optional[BlogContentRepository] = None
        self.blog_processing_service: Optional[BlogProcessingService] = None
        
        self.running = False
        self.start_time = time.time()
        
        logger.info(f"🔧 Worker initialized (poll interval: {config.poll_interval_seconds}s)")
    
    async def start(self):
        """Start the worker."""
        logger.info("🚀 Starting Worker Service...")
        
        # Connect to MongoDB
        await self.db_manager.connect(
            mongodb_url=self.config.mongodb_url,
            database_name=self.config.database_name,
            username=self.config.mongodb_username,
            password=self.config.mongodb_password
        )
        logger.info("✅ MongoDB connected")
        
        # Initialize dependencies using factory functions (pure DI)
        # These are called after DB connection to handle lifecycle-dependent dependencies
        
        # 1. Create PublisherRepository (requires DB connection)
        self.publisher_repo = await self.publisher_repo_factory(self.config.postgres_url)
        await self.publisher_repo.connect()
        logger.info("✅ PostgreSQL connected")
        
        # 2. Create repositories that depend on MongoDB connection
        self.storage = self.storage_factory()
        self.job_repo = self.job_repo_factory()
        await self.job_repo.create_indexes()
        logger.info("✅ Job repository initialized")
        
        # 3. Create LLM service
        self.llm_service = self.llm_service_factory()
        logger.info("✅ LLM service initialized")
        
        # 4. Create specialized services using factories (pure DI)
        content_retrieval_service = self.content_retrieval_service_factory(self.crawler, self.storage)
        threshold_service = self.threshold_service_factory(self.storage, self.job_repo)
        llm_generation_service = self.llm_generation_service_factory(self.llm_service)
        
        # 5. Create blog processing service using factory (pure DI)
        self.blog_processing_service = self.blog_processing_service_factory(
            self.job_repo,
            self.publisher_repo,
            self.storage,
            content_retrieval_service,
            threshold_service,
            llm_generation_service
        )
        logger.info("✅ Blog processing service initialized")
        
        # Start metrics server
        start_metrics_server(self.config.metrics_port)
        logger.info("✅ Metrics server started")
        
        # Start polling loop
        self.running = True
        await self.poll_loop()
    
    async def stop(self):
        """Stop the worker gracefully."""
        logger.info("🛑 Stopping worker...")
        self.running = False
        
        # Close database connections
        if self.publisher_repo:
            await self.publisher_repo.disconnect()
        if self.db_manager:
            await self.db_manager.close()
    
    async def poll_loop(self):
        """Main polling loop."""
        logger.info("🔄 Starting polling loop...")
        
        # Update uptime gauge
        async def update_uptime():
            """Periodically update uptime metric."""
            while self.running:
                worker_uptime_seconds.set(time.time() - self.start_time)
                await asyncio.sleep(10)
        
        # Start uptime updater
        asyncio.create_task(update_uptime())
        
        # Update queue size periodically
        async def update_queue_size():
            """Periodically update queue size metrics."""
            while self.running:
                try:
                    if self.job_repo:
                        # Use single aggregation query instead of 4 separate count queries
                        pipeline = [
                            {
                                "$group": {
                                    "_id": "$status",
                                    "count": {"$sum": 1}
                                }
                            }
                        ]
                        results = await self.job_repo.collection.aggregate(pipeline).to_list(length=None)
                        
                        # Initialize all statuses to 0
                        status_counts = {
                            "pending": 0,
                            "processing": 0,
                            "completed": 0,
                            "failed": 0,
                            "skipped": 0
                        }
                        
                        # Update with actual counts from aggregation
                        for result in results:
                            status = result["_id"]
                            if status in status_counts:
                                status_counts[status] = result["count"]
                        
                        # Update metrics
                        job_queue_size.labels(status="pending").set(status_counts["pending"])
                        job_queue_size.labels(status="processing").set(status_counts["processing"])
                        job_queue_size.labels(status="completed").set(status_counts["completed"])
                        job_queue_size.labels(status="failed").set(status_counts["failed"])
                        job_queue_size.labels(status="skipped").set(status_counts["skipped"])
                except Exception as e:
                    logger.debug(f"Error updating queue size: {e}")
                await asyncio.sleep(30)
        
        # Start queue size updater
        asyncio.create_task(update_queue_size())
        
        while self.running:
            try:
                poll_iterations_total.inc()
                
                # Get next job
                job = await self.job_repo.get_next_queued_job()
                
                if job:
                    logger.info(f"📥 Found job: {job.job_id} ({job.blog_url})")
                    # Extract domain for metrics using shared utility
                    publisher_domain = extract_domain(job.blog_url)
                    
                    # Record job polled
                    jobs_polled_total.labels(publisher_domain=publisher_domain).inc()
                    
                    await self.process_job(job)
                else:
                    # No jobs, wait before next poll
                    await asyncio.sleep(self.config.poll_interval_seconds)
                
            except Exception as e:
                poll_errors_total.inc()
                logger.error(f"❌ Error in poll loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.poll_interval_seconds)
    
    async def process_job(self, job: ProcessingJob):
        """
        Process a single job.
        
        Args:
            job: Job to process
        """
        await self.blog_processing_service.process_job(job)


# Global worker instance
worker: Optional[BlogProcessingWorker] = None


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"📡 Received signal {signum}")
    if worker:
        asyncio.create_task(worker.stop())


async def main():
    """Main entry point."""
    global worker
    
    # Load .env file into os.environ so LLM library can read API keys
    # This is needed because the library reads from os.getenv() when api_key=None
    load_dotenv()
    
    # Load configuration
    config = get_config()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create dependencies - pure DI pattern (all dependencies injected, nothing created in worker)
    db_manager = DatabaseManager()
    crawler = BlogCrawler()
    
    # Create factory functions for lifecycle-dependent dependencies
    # These factories will be called in worker.start() after DB connection
    
    async def create_publisher_repo(postgres_url: str) -> PublisherRepository:
        """Factory function for PublisherRepository."""
        return PublisherRepository(postgres_url)
    
    def create_job_repo() -> JobRepository:
        """Factory function for JobRepository (captures db_manager.database from closure)."""
        # Closure captures db_manager reference; db_manager.database will be available when called in start()
        return JobRepository(db_manager.database)
    
    def create_storage() -> BlogContentRepository:
        """Factory function for BlogContentRepository (captures db_manager.database from closure)."""
        # Closure captures db_manager reference; db_manager.database will be available when called in start()
        return BlogContentRepository(database=db_manager.database)
    
    def create_llm_service() -> LLMContentGenerator:
        """Factory function for LLMContentGenerator."""
        # API keys are read from env vars by the LLM library itself (BaseSettings pattern)
        return LLMContentGenerator(
            model=config.openai_model or None
        )
    
    def create_content_retrieval_service(crawler: BlogCrawler, storage: BlogContentRepository) -> ContentRetrievalService:
        """Factory function for ContentRetrievalService."""
        return ContentRetrievalService(crawler=crawler, storage=storage)
    
    def create_threshold_service(storage: BlogContentRepository, job_repo: JobRepository) -> ThresholdService:
        """Factory function for ThresholdService."""
        return ThresholdService(storage=storage, job_repo=job_repo)
    
    def create_llm_generation_service(llm_service: LLMContentGenerator) -> LLMGenerationService:
        """Factory function for LLMGenerationService."""
        return LLMGenerationService(llm_service=llm_service)
    
    def create_blog_processing_service(
        job_repo: JobRepository,
        publisher_repo: PublisherRepository,
        storage: BlogContentRepository,
        content_retrieval_service: ContentRetrievalService,
        threshold_service: ThresholdService,
        llm_generation_service: LLMGenerationService
    ) -> BlogProcessingService:
        """Factory function for BlogProcessingService."""
        return BlogProcessingService(
            job_repo=job_repo,
            publisher_repo=publisher_repo,
            storage=storage,
            content_retrieval_service=content_retrieval_service,
            threshold_service=threshold_service,
            llm_generation_service=llm_generation_service
        )
    
    # Create and start worker with injected dependencies and factories
    worker = BlogProcessingWorker(
        config=config,
        db_manager=db_manager,
        crawler=crawler,
        publisher_repo_factory=create_publisher_repo,
        job_repo_factory=create_job_repo,
        storage_factory=create_storage,
        llm_service_factory=create_llm_service,
        content_retrieval_service_factory=create_content_retrieval_service,
        threshold_service_factory=create_threshold_service,
        llm_generation_service_factory=create_llm_generation_service,
        blog_processing_service_factory=create_blog_processing_service
    )
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt received")
    finally:
        await worker.stop()  # stop() now handles database cleanup
        logger.info("👋 Worker shut down")


if __name__ == "__main__":
    asyncio.run(main())

