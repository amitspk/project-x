"""Worker service - polls for jobs and processes them."""

import asyncio
import logging
import os
import signal
import time
from datetime import datetime
from typing import Optional, Callable, Coroutine, Any, Dict, List
from dotenv import load_dotenv

from fyi_widget_worker_service.core.database import DatabaseManager
from fyi_widget_worker_service.repositories import JobRepository, PublisherRepository
from fyi_widget_worker_service.repositories.blog_processing_queue_repository import BlogProcessingQueueRepository
from fyi_widget_worker_service.repositories.blog_processing_audit_repository import BlogProcessingAuditRepository
from fyi_widget_worker_service.models.blog_processing_models import BlogProcessingStatus, AuditStatus
from fyi_widget_worker_service.services.blog_crawler import BlogCrawler
from fyi_widget_worker_service.services.llm_content_generator import LLMContentGenerator
from fyi_widget_worker_service.services.blog_content_repository import BlogContentRepository
from fyi_widget_worker_service.utils import extract_domain

# Import configuration
from fyi_widget_worker_service.core.config import get_config, WorkerServiceConfig

# Import services
from fyi_widget_worker_service.services.content_retrieval_service import ContentRetrievalService
from fyi_widget_worker_service.services.llm_generation_service import LLMGenerationService

# Import metrics
from fyi_widget_worker_service.core.metrics import (
    job_queue_size,
    poll_iterations_total,
    poll_errors_total,
    worker_uptime_seconds,
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
        blog_queue_repo_factory: Callable[[], BlogProcessingQueueRepository],  # V2: blog_processing_queue
        blog_audit_repo_factory: Callable[[], BlogProcessingAuditRepository],  # V2: blog_processing_audit
        llm_service_factory: Callable[[], LLMContentGenerator],
        content_retrieval_service_factory: Callable[[BlogCrawler, BlogContentRepository], ContentRetrievalService],
        llm_generation_service_factory: Callable[[LLMContentGenerator, asyncio.Semaphore], LLMGenerationService],
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
            job_repo_factory: Factory function that takes no args (uses self.db_manager.database) and returns JobRepository (V1)
            storage_factory: Factory function that takes no args (uses self.db_manager.database) and returns BlogContentRepository
            blog_queue_repo_factory: Factory function that returns BlogProcessingQueueRepository (V2 architecture)
            blog_audit_repo_factory: Factory function that returns BlogProcessingAuditRepository (V2 architecture)
            llm_service_factory: Factory function that takes no args and returns LLMContentGenerator
            content_retrieval_service_factory: Factory function that creates ContentRetrievalService
            llm_generation_service_factory: Factory function that creates LLMGenerationService
        """
        self.config = config
        self.db_manager = db_manager
        self.crawler = crawler
        
        # Store factory functions
        self.publisher_repo_factory = publisher_repo_factory
        self.job_repo_factory = job_repo_factory
        self.storage_factory = storage_factory
        self.blog_queue_repo_factory = blog_queue_repo_factory
        self.blog_audit_repo_factory = blog_audit_repo_factory
        self.llm_service_factory = llm_service_factory
        self.content_retrieval_service_factory = content_retrieval_service_factory
        self.llm_generation_service_factory = llm_generation_service_factory
        
        # Dependencies (initialized in start() using factory functions)
        self.job_repo: Optional[JobRepository] = None  # V1 (legacy)
        self.blog_queue_repo: Optional[BlogProcessingQueueRepository] = None  # V2
        self.blog_audit_repo: Optional[BlogProcessingAuditRepository] = None  # V2
        self.publisher_repo: Optional[PublisherRepository] = None
        self.llm_service: Optional[LLMContentGenerator] = None
        self.storage: Optional[BlogContentRepository] = None
        
        # Worker ID for tracking (used in heartbeats and audit)
        self.worker_id = f"worker_{os.getpid()}"
        
        # LLM rate limiting semaphore (controls concurrent LLM API calls)
        self.llm_semaphore = asyncio.Semaphore(self.config.llm_rate_limit)
        
        self.running = False
        self.start_time = time.time()
        
        logger.info(
            f"🔧 Worker initialized (poll interval: {config.poll_interval_seconds}s, "
            f"batch: {config.batch_size}, concurrent: {config.concurrent_processing_limit}, "
            f"LLM limit: {config.llm_rate_limit})"
        )
    
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
        
        # V1 repository (legacy)
        self.job_repo = self.job_repo_factory()
        await self.job_repo.create_indexes()
        logger.info("✅ Job repository initialized (V1)")
        
        # V2 repositories (new architecture)
        self.blog_queue_repo = self.blog_queue_repo_factory()
        await self.blog_queue_repo.create_indexes()
        logger.info("✅ Blog queue repository initialized (V2)")
        
        self.blog_audit_repo = self.blog_audit_repo_factory()
        await self.blog_audit_repo.create_indexes()
        logger.info("✅ Blog audit repository initialized (V2)")
        
        # 3. Create LLM service
        self.llm_service = self.llm_service_factory()
        logger.info("✅ LLM service initialized")
        
        # 4. Create specialized services using factories (pure DI)
        content_retrieval_service = self.content_retrieval_service_factory(self.crawler, self.storage)
        llm_generation_service = self.llm_generation_service_factory(self.llm_service, self.llm_semaphore)
        logger.info("✅ Worker services initialized (V3 architecture - batch + parallel processing with rate limiting)")
        
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
        
        # ========================================================================
        # V2: HEARTBEAT UPDATER
        # ========================================================================
        # Periodically update heartbeat for any blog being processed by this worker
        async def update_heartbeat():
            """Periodically update heartbeat for current job."""
            while self.running:
                try:
                    # Update heartbeat for all blogs currently being processed by this worker
                    await self.blog_queue_repo.update_heartbeat(self.worker_id)
                except Exception as e:
                    logger.debug(f"Error updating heartbeat: {e}")
                await asyncio.sleep(15)  # Update every 15 seconds (half of 30s interval)
        
        # Start heartbeat updater
        asyncio.create_task(update_heartbeat())
        logger.info(f"✅ Heartbeat updater started (worker_id: {self.worker_id})")
        
        # ========================================================================
        # V3 POLLING LOGIC - Batch processing with parallel execution
        # ========================================================================
        logger.info(
            f"🔄 Starting batch polling loop "
            f"(batch_size={self.config.batch_size}, "
            f"concurrent_limit={self.config.concurrent_processing_limit})"
        )
        
        while self.running:
            try:
                poll_iterations_total.inc()
                
                # ============================================================
                # STEP 1: Pick batch of blogs atomically
                # ============================================================
                blogs = await self.blog_queue_repo.atomic_batch_pick_sequential(
                    worker_id=self.worker_id,
                    batch_size=self.config.batch_size
                )
                
                if blogs:
                    batch_start_time = time.time()
                    
                    logger.info(
                        f"📥 [{self.worker_id}] Picked batch of {len(blogs)} blogs"
                    )
                    
                    # ============================================================
                    # STEP 2: Process batch in parallel (controlled groups)
                    # ============================================================
                    await self.process_batch_in_groups(
                        blogs,
                        group_size=self.config.concurrent_processing_limit
                    )
                    
                    batch_duration = time.time() - batch_start_time
                    logger.info(
                        f"✅ [{self.worker_id}] Completed batch of {len(blogs)} blogs "
                        f"in {batch_duration:.2f}s "
                        f"(avg: {batch_duration/len(blogs):.2f}s per blog)"
                    )
                    
                else:
                    # No jobs, wait before next poll
                    logger.debug(
                        f"[{self.worker_id}] 😴 No jobs in queue, sleeping..."
                    )
                    await asyncio.sleep(self.config.poll_interval_seconds)
                
            except Exception as e:
                poll_errors_total.inc()
                logger.error(
                    f"❌ Error in batch poll loop: {e}",
                    exc_info=True
                )
                await asyncio.sleep(self.config.poll_interval_seconds)
    
    async def process_batch_in_groups(
        self,
        blogs: List[dict],
        group_size: int = 5
    ):
        """
        Process blogs in controlled groups for optimal resource usage.
        
        Why groups instead of all at once?
        - Prevents overwhelming MongoDB connection pool
        - Prevents overwhelming PostgreSQL connection pool
        - Prevents overwhelming LLM API rate limits
        - Better error isolation
        - More predictable memory usage
        
        Example:
            If batch_size=20 and group_size=5:
            - Process blogs 0-4 in parallel
            - Wait for all 5 to complete
            - Process blogs 5-9 in parallel
            - Wait for all 5 to complete
            - Continue...
        
        Args:
            blogs: List of blog entries to process
            group_size: Number of blogs to process concurrently
        """
        total_blogs = len(blogs)
        total_groups = (total_blogs + group_size - 1) // group_size
        
        logger.info(
            f"[{self.worker_id}] 🔄 Processing {total_blogs} blogs "
            f"in {total_groups} groups of {group_size}"
        )
        
        for group_index in range(0, total_blogs, group_size):
            group = blogs[group_index:group_index + group_size]
            group_num = (group_index // group_size) + 1
            
            logger.info(
                f"[{self.worker_id}] 📦 Processing group {group_num}/{total_groups} "
                f"({len(group)} blogs)"
            )
            
            # Create tasks for this group
            tasks = []
            for blog in group:
                task = asyncio.create_task(self.process_blog_v2_safe(blog))
                tasks.append(task)
            
            # Wait for all tasks in this group to complete
            # return_exceptions=True ensures one failure doesn't stop others
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            success_count = sum(
                1 for r in results if not isinstance(r, Exception)
            )
            failure_count = len(group) - success_count
            
            logger.info(
                f"[{self.worker_id}] ✅ Group {group_num}/{total_groups} complete: "
                f"{success_count} succeeded, {failure_count} failed"
            )
            
            # Brief pause between groups to prevent thundering herd
            if group_index + group_size < total_blogs:
                await asyncio.sleep(0.5)
    
    async def process_blog_v2_safe(self, blog_entry: dict):
        """
        Wrapper around process_blog_v2 with comprehensive error handling.
        
        This ensures one blog's failure doesn't affect others in the batch.
        All errors are caught, logged, and handled gracefully.
        
        Args:
            blog_entry: Blog entry from blog_processing_queue
        """
        url = blog_entry.get("url")
        attempt = blog_entry.get("attempt_count", 1)
        
        try:
            # Call existing process_blog_v2 logic
            await self.process_blog_v2(blog_entry)
            
        except Exception as e:
            # This is a safety net - process_blog_v2 already has error handling
            # But we catch here to ensure the batch continues
            logger.error(
                f"❌ [{self.worker_id}] Unexpected error in process_blog_v2_safe "
                f"for {url} (attempt {attempt}): {e}",
                exc_info=True
            )
            
            # The error is already handled in process_blog_v2
            # (status updated to RETRY or FAILED, audit entry written)
            # So we just log and continue
    
    async def process_blog_v2(self, blog_entry: Dict[str, Any]):
        """
        Process a blog using V2 architecture (blog_processing_queue + audit trail).
        
        This method:
        1. Fetches publisher config
        2. Crawls/retrieves blog content
        3. Generates summary, questions, and embeddings using LLM
        4. Saves results to processed_questions collection
        5. Updates blog_processing_queue status (completed/retry/failed)
        6. Writes audit trail entry
        
        Args:
            blog_entry: Dictionary from blog_processing_queue collection
        """
        url = blog_entry.get("url")
        publisher_id = blog_entry.get("publisher_id")
        attempt = blog_entry.get("attempt_count", 1)
        was_previously_completed = blog_entry.get("was_previously_completed", False)
        start_time = time.time()
        publisher_domain = extract_domain(url)
        
        try:
            logger.info(f"🔄 [{self.worker_id}] Processing blog: {url} (attempt {attempt}/3)")
            
            # Step 1: Get publisher config
            publisher = await self.publisher_repo.get_publisher_by_id(publisher_id)
            if not publisher:
                raise ValueError(f"Publisher not found: {publisher_id}")
            
            config = publisher.config
            logger.info(f"📋 Config: {config.questions_per_blog} questions")
            
            # Step 2: Get blog content (from cache or crawl)
            content_retrieval_service = self.content_retrieval_service_factory(self.crawler, self.storage)
            crawl_result, blog_id, blog_doc = await content_retrieval_service.get_blog_content(
                url=url,
                publisher_domain=publisher_domain
            )
            
            # Step 3: Generate LLM content
            llm_generation_service = self.llm_generation_service_factory(self.llm_service, self.llm_semaphore)
            
            summary_text, key_points, llm_generated_title = await llm_generation_service.generate_summary(
                crawl_result=crawl_result,
                config=config,
                publisher_domain=publisher_domain
            )
            
            questions = await llm_generation_service.generate_questions(
                crawl_result=crawl_result,
                config=config,
                publisher_domain=publisher_domain
            )
            
            summary_embedding, question_embeddings = await llm_generation_service.generate_embeddings(
                summary_text=summary_text,
                questions=questions,
                publisher_domain=publisher_domain
            )
            
            # Step 4: Save results to database
            final_title = llm_generated_title if llm_generated_title else crawl_result.title
            
            # Save summary
            summary_id = await self.storage.save_summary(
                blog_id=blog_id,
                blog_url=url,
                summary_text=summary_text,
                key_points=key_points,
                embedding=summary_embedding,
                title=final_title
            )
            
            # Prepare questions for bulk save
            questions_to_save = []
            embeddings_to_save = []
            question_count = 0
            for q_text, q_answer, q_category, q_confidence in questions:
                if q_confidence is not None and q_confidence < 0.5:
                    continue
                
                q_embedding = question_embeddings[question_count] if question_count < len(question_embeddings) else None
                questions_to_save.append({
                    "question": q_text,
                    "answer": q_answer,
                    "keyword_anchor": q_category or "general",  # Map category to keyword_anchor
                    "probability": q_confidence  # Map confidence to probability
                })
                if q_embedding:
                    embeddings_to_save.append(q_embedding)
                question_count += 1
            
            # Save all questions
            if questions_to_save:
                await self.storage.save_questions(
                    blog_id=blog_id,
                    blog_url=url,
                    questions=questions_to_save,
                    embeddings=embeddings_to_save if embeddings_to_save else None
                )
            
            processing_duration = time.time() - start_time
            
            # Step 5: Mark as completed in blog_processing_queue
            await self.blog_queue_repo.atomic_update_status(
                url=url,
                from_status=BlogProcessingStatus.PROCESSING,
                to_status=BlogProcessingStatus.COMPLETED,
                updates={
                    "completed_at": datetime.utcnow(),
                    "last_error": None,
                    "error_type": None,
                }
            )
            
            # Step 6: Release blog slot and record successful processing
            # Skip if this is a reprocess of an already-completed blog (stats already counted)
            if not was_previously_completed:
                await self.publisher_repo.release_blog_slot(
                    publisher_id=publisher_id,
                    processed=True,
                    questions_generated=question_count
                )
                logger.info(f"[{self.worker_id}] ✅ Released slot and recorded processing")
            else:
                logger.info(
                    f"[{self.worker_id}] ♻️  Reprocessed completed blog - "
                    f"questions updated but stats not recounted (already processed)"
                )
            
            # Step 7: Write audit entry (success)
            await self.blog_audit_repo.insert_audit_entry(
                url=url,
                publisher_id=publisher_id,
                job_id=None,  # V2: No job_id
                worker_id=self.worker_id,
                status=AuditStatus.COMPLETED,
                attempt_number=attempt,
                processing_time_seconds=processing_duration,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                question_count=question_count,
                summary_length=len(summary_text),
            )
            
            logger.info(
                f"✅ [{self.worker_id}] Successfully processed: {url} "
                f"({question_count} questions, {processing_duration:.2f}s)"
            )
            
        except Exception as e:
            processing_duration = time.time() - start_time
            error_message = str(e)
            error_type = type(e).__name__
            
            logger.error(
                f"❌ [{self.worker_id}] Failed to process {url}: {e} "
                f"(duration: {processing_duration:.2f}s, attempt {attempt}/3)",
                exc_info=True
            )
            
            # Determine next status based on attempt count
            if attempt < 3:
                # Retry
                next_status = BlogProcessingStatus.RETRY
                logger.info(f"🔄 [{self.worker_id}] Will retry {url} (attempt {attempt + 1}/3)")
            else:
                # Failed permanently
                next_status = BlogProcessingStatus.FAILED
                logger.error(f"💀 [{self.worker_id}] Permanently failed {url} after 3 attempts")
            
            # Update blog_processing_queue
            await self.blog_queue_repo.atomic_update_status(
                url=url,
                from_status=BlogProcessingStatus.PROCESSING,
                to_status=next_status,
                updates={
                    "last_error": error_message[:500],  # Truncate to 500 chars
                    "error_type": error_type,
                    "worker_id": None if next_status == BlogProcessingStatus.FAILED else self.worker_id,
                }
            )
            
            # Release slot if permanently failed (not for retry)
            # Skip if this is a reprocess of completed blog (no slot was reserved)
            if next_status == BlogProcessingStatus.FAILED and not was_previously_completed:
                await self.publisher_repo.release_blog_slot(
                    publisher_id=publisher_id,
                    processed=False
                )
                logger.info(f"[{self.worker_id}] ✅ Released slot for failed blog")
            
            # Write audit entry (failure)
            await self.blog_audit_repo.insert_audit_entry(
                url=url,
                publisher_id=publisher_id,
                job_id=None,  # V2: No job_id
                worker_id=self.worker_id,
                status=AuditStatus.FAILED,
                attempt_number=attempt,
                processing_time_seconds=processing_duration,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message=error_message[:500],
                error_type=error_type,
            )
            
            # Don't re-raise - we've handled the error by updating status
            # The worker should continue to the next job


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
    
    def create_blog_queue_repo() -> BlogProcessingQueueRepository:
        """Factory function for BlogProcessingQueueRepository (v2 architecture)."""
        # Closure captures db_manager reference; db_manager.database will be available when called in start()
        return BlogProcessingQueueRepository(database=db_manager.database)
    
    def create_blog_audit_repo() -> BlogProcessingAuditRepository:
        """Factory function for BlogProcessingAuditRepository (v2 architecture)."""
        # Closure captures db_manager reference; db_manager.database will be available when called in start()
        return BlogProcessingAuditRepository(database=db_manager.database)
    
    def create_llm_service() -> LLMContentGenerator:
        """Factory function for LLMContentGenerator."""
        # API keys are read from env vars by the LLM library itself (BaseSettings pattern)
        return LLMContentGenerator(
            model=config.openai_model or None
        )
    
    def create_content_retrieval_service(crawler: BlogCrawler, storage: BlogContentRepository) -> ContentRetrievalService:
        """Factory function for ContentRetrievalService."""
        return ContentRetrievalService(crawler=crawler, storage=storage)
    
    def create_llm_generation_service(llm_service: LLMContentGenerator, semaphore: asyncio.Semaphore) -> LLMGenerationService:
        """Factory function for LLMGenerationService with rate limiting."""
        return LLMGenerationService(llm_service=llm_service, semaphore=semaphore)
    
    # Create and start worker with injected dependencies and factories
    worker = BlogProcessingWorker(
        config=config,
        db_manager=db_manager,
        crawler=crawler,
        publisher_repo_factory=create_publisher_repo,
        job_repo_factory=create_job_repo,
        storage_factory=create_storage,
        blog_queue_repo_factory=create_blog_queue_repo,  # V2
        blog_audit_repo_factory=create_blog_audit_repo,  # V2
        llm_service_factory=create_llm_service,
        content_retrieval_service_factory=create_content_retrieval_service,
        llm_generation_service_factory=create_llm_generation_service,
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

