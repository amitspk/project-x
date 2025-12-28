"""Worker service - polls for jobs and processes them."""

import asyncio
import logging
import signal
import time
from typing import Optional

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

# Import metrics
from fyi_widget_worker_service.core.metrics import (
    jobs_polled_total,
    jobs_processed_total,
    job_processing_duration_seconds,
    jobs_processing_active,
    job_queue_size,
    crawl_operations_total,
    crawl_duration_seconds,
    crawl_content_size_bytes,
    crawl_word_count,
    llm_operations_total,
    llm_operation_duration_seconds,
    llm_tokens_used_total,
    questions_generated_total,
    questions_per_blog,
    embeddings_generated_total,
    blogs_processed_total,
    worker_uptime_seconds,
    poll_iterations_total,
    poll_errors_total,
    processing_errors_total,
    db_operations_total,
    db_operation_duration_seconds
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
        db_manager: Optional[DatabaseManager] = None,
        crawler: Optional[BlogCrawler] = None
    ):
        """
        Initialize worker with configuration and dependencies.
        
        Args:
            config: Worker service configuration
            db_manager: DatabaseManager instance (optional, will create if not provided)
                       Injected for better testability - can be mocked in tests
            crawler: CrawlerService instance (optional, will create if not provided)
                    Injected for better testability - can be mocked in tests
        """
        self.config = config
        self.db_manager = db_manager if db_manager is not None else DatabaseManager()
        self.job_repo: Optional[JobRepository] = None
        self.publisher_repo: Optional[PublisherRepository] = None
        self.running = False
        self.start_time = time.time()
        
        # Inject services that don't need DB (for better testability)
        self.crawler = crawler if crawler is not None else BlogCrawler()
        
        # Services (initialized after DB connection in start() method)
        # Note: These are created after DB connection because they require DB access.
        # This is acceptable for lifecycle-dependent services.
        self.llm_service: Optional[LLMContentGenerator] = None
        self.storage: Optional[BlogContentRepository] = None
        self.blog_processing_service: Optional[BlogProcessingService] = None
        
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
        
        # Connect to PostgreSQL for publisher configs
        self.publisher_repo = PublisherRepository(self.config.postgres_url)
        await self.publisher_repo.connect()
        logger.info("✅ PostgreSQL connected")
        
        # Initialize services now that we have database
        # Note: BlogCrawler is already initialized via constructor injection
        # Note: LLMContentGenerator model will be set per-job based on publisher config
        # We'll create LLMContentGenerator instances per job with the correct model
        self.storage = BlogContentRepository(database=self.db_manager.database)
        # LLM service will be created per-job with publisher's model
        # Create a base LLMContentGenerator instance (model will be set per-job)
        self.llm_service = LLMContentGenerator(api_key=None, model=None)
        logger.info("✅ Services initialized")
        
        # Initialize job repository
        self.job_repo = JobRepository(self.db_manager.database)
        await self.job_repo.create_indexes()
        logger.info("✅ Job repository initialized")
        
        # Initialize specialized services for blog processing (pure DI)
        from fyi_widget_worker_service.services.content_retrieval_service import ContentRetrievalService
        from fyi_widget_worker_service.services.threshold_service import ThresholdService
        from fyi_widget_worker_service.services.llm_generation_service import LLMGenerationService
        
        content_retrieval_service = ContentRetrievalService(
            crawler=self.crawler,
            storage=self.storage
        )
        
        threshold_service = ThresholdService(
            storage=self.storage,
            job_repo=self.job_repo
        )
        
        llm_generation_service = LLMGenerationService(
            llm_service=self.llm_service
        )
        
        # Initialize blog processing service with injected services (pure DI)
        self.blog_processing_service = BlogProcessingService(
            job_repo=self.job_repo,
            publisher_repo=self.publisher_repo,
            storage=self.storage,  # Storage is needed by orchestrator
            content_retrieval_service=content_retrieval_service,
            threshold_service=threshold_service,
            llm_generation_service=llm_generation_service
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
    
    # Load configuration
    config = get_config()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start worker
    worker = BlogProcessingWorker(config=config)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt received")
    finally:
        await worker.stop()
        logger.info("👋 Worker shut down")


if __name__ == "__main__":
    asyncio.run(main())

