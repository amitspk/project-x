"""Worker service - polls for jobs and processes them."""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Add shared to path
sys.path.append(str(Path(__file__).parent.parent))

from fyi_widget_shared_library.data import JobRepository, DatabaseManager
from fyi_widget_shared_library.data.postgres_database import PostgresPublisherRepository
from fyi_widget_shared_library.models import ProcessingJob, JobStatus, JobResult
from fyi_widget_shared_library.models.publisher import PublisherConfig
from fyi_widget_shared_library.services import CrawlerService, LLMService, StorageService
from fyi_widget_shared_library.services.llm_prompts import (
    DEFAULT_QUESTIONS_PROMPT,
    QUESTIONS_JSON_FORMAT,
    OUTPUT_FORMAT_INSTRUCTION,
)
from fyi_widget_shared_library.utils import normalize_url

# Import metrics
from metrics import (
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
from metrics_server import start_metrics_server

# Configuration from environment
import os
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME", "admin")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "password123")
DATABASE_NAME = os.getenv("DATABASE_NAME", "blog_qa_db")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/blog_qa_publishers")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BlogProcessingWorker:
    """Worker that polls for jobs and processes blogs."""
    
    def __init__(self):
        """Initialize worker."""
        self.db_manager = DatabaseManager()
        self.job_repo: Optional[JobRepository] = None
        self.publisher_repo: Optional[PostgresPublisherRepository] = None
        self.running = False
        self.start_time = time.time()
        
        # Services (initialized after DB connection)
        self.crawler = None
        self.llm_service = None
        self.storage = None
        
        logger.info(f"🔧 Worker initialized (poll interval: {POLL_INTERVAL}s)")
    
    async def start(self):
        """Start the worker."""
        logger.info("🚀 Starting Worker Service...")
        
        # Connect to MongoDB
        await self.db_manager.connect(
            mongodb_url=MONGODB_URL,
            database_name=DATABASE_NAME,
            username=MONGODB_USERNAME,
            password=MONGODB_PASSWORD
        )
        logger.info("✅ MongoDB connected")
        
        # Connect to PostgreSQL for publisher configs
        self.publisher_repo = PostgresPublisherRepository(POSTGRES_URL)
        await self.publisher_repo.connect()
        logger.info("✅ PostgreSQL connected")
        
        # Initialize services now that we have database
        # Note: LLMService model will be set per-job based on publisher config
        # We'll create LLMService instances per job with the correct model
        self.crawler = CrawlerService()
        self.storage = StorageService(database=self.db_manager.database)
        # LLM service will be created per-job with publisher's model
        logger.info("✅ Services initialized")
        
        # Initialize job repository
        self.job_repo = JobRepository(self.db_manager.database)
        await self.job_repo.create_indexes()
        logger.info("✅ Job repository initialized")
        
        # Start metrics server
        start_metrics_server()
        logger.info("✅ Metrics server started")
        
        # Start polling loop
        self.running = True
        await self.poll_loop()
    
    async def stop(self):
        """Stop the worker gracefully."""
        logger.info("🛑 Stopping worker...")
        self.running = False
    
    async def get_publisher_config(self, blog_url: str) -> PublisherConfig:
        """
        Fetch publisher config by extracting domain from URL.
        Falls back to default config if publisher not found.
        
        Args:
            blog_url: Blog URL to extract domain from
            
        Returns:
            PublisherConfig object
        """
        try:
            from urllib.parse import urlparse
            
            # Extract domain
            parsed = urlparse(blog_url if blog_url.startswith('http') else f'https://{blog_url}')
            domain = parsed.netloc or parsed.path
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Fetch publisher - first try exact match, then try subdomain matching
            publisher = await self.publisher_repo.get_publisher_by_domain(domain, allow_subdomain=True)
            
            if publisher:
                logger.info(f"✅ Using config for publisher: {publisher.name} (domain: {publisher.domain}) - matched from blog URL domain: {domain}")
                return publisher.config
            else:
                logger.warning(f"⚠️  Publisher not found for domain: {domain}, using defaults")
                return PublisherConfig()  # Default config
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to fetch publisher config: {e}, using defaults")
            return PublisherConfig()  # Default config
    
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
                    # Extract domain for metrics
                    from urllib.parse import urlparse
                    parsed = urlparse(job.blog_url if job.blog_url.startswith('http') else f'https://{job.blog_url}')
                    domain = parsed.netloc or parsed.path
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    publisher_domain = domain.lower()
                    publisher = None
                    
                    # Record job polled
                    jobs_polled_total.labels(publisher_domain=publisher_domain).inc()
                    
                    await self.process_job(job)
                else:
                    # No jobs, wait before next poll
                    await asyncio.sleep(POLL_INTERVAL)
                
            except Exception as e:
                poll_errors_total.inc()
                logger.error(f"❌ Error in poll loop: {e}", exc_info=True)
                await asyncio.sleep(POLL_INTERVAL)
    
    async def process_job(self, job: ProcessingJob):
        """
        Process a single job.
        
        Args:
            job: Job to process
        """
        start_time = time.time()
        
        # Extract domain for metrics
        from urllib.parse import urlparse
        parsed = urlparse(job.blog_url if job.blog_url.startswith('http') else f'https://{job.blog_url}')
        domain = parsed.netloc or parsed.path
        if domain.startswith('www.'):
            domain = domain[4:]
        publisher_domain = domain.lower()
        
        # Initialize blog_id to track if raw content was saved
        blog_id = None
        
        try:
            # Mark as processing
            success = await self.job_repo.mark_job_processing(job.job_id)
            if not success:
                logger.warning(f"⚠️  Could not lock job {job.job_id}, skipping")
                return
            
            logger.info(f"🔄 Processing job {job.job_id}...")
            
            # Track active job
            jobs_processing_active.labels(publisher_domain=publisher_domain).inc()
            
            # Normalize URL before processing
            normalized_url = normalize_url(job.blog_url)
            if normalized_url != job.blog_url:
                logger.info(f"   Normalized URL: {normalized_url}")
            
            # For testing: if URL contains localhost, use hardcoded test URL for crawling
            # This allows testing with localhost URLs while using real content
            TEST_CRAWL_URL = "https://www.rushlane.com/new-kia-clarens-clavis-hte-ex-launch-price-rs-12-55-l-12538043.html"
            if "localhost" in normalized_url.lower():
                logger.info(f"🔄 Localhost URL detected, using test URL for crawling: {TEST_CRAWL_URL}")
                crawl_url = TEST_CRAWL_URL
            else:
                crawl_url = normalized_url
            
            # Fetch publisher config (use original normalized_url, not crawl_url)
            config = await self.get_publisher_config(normalized_url)
            
            # Helper function to get model value
            def get_model(model_field):
                """Get model value from enum."""
                if model_field is not None:
                    return model_field.value if hasattr(model_field, 'value') else str(model_field)
                return None  # LLMService will use DEFAULT_MODEL
            
            # Get models for each operation
            summary_model = get_model(config.summary_model)
            questions_model = get_model(config.questions_model)
            
            logger.info(f"📋 Config: {config.questions_per_blog} questions")
            logger.info(f"🤖 Models - Summary: {summary_model}, Questions: {questions_model}")
            logger.info(f"🌡️  Temperatures - Summary: {config.summary_temperature}, Questions: {config.questions_temperature}")
            logger.info(f"🔢 Max Tokens - Summary: {config.summary_max_tokens}, Questions: {config.questions_max_tokens}")
            
            # Create LLM service (can use any model as default, will be overridden per operation)
            # We'll use questions_model as the instance default since it's used most
            default_model = questions_model or summary_model
            self.llm_service = LLMService(api_key=None, model=default_model)
            logger.info(f"🤖 LLM Service initialized with default model: {default_model}")
            
            # Log prompt configuration
            has_custom_question = config.custom_question_prompt is not None
            has_custom_summary = config.custom_summary_prompt is not None
            logger.info(
                f"🎯 Prompts: "
                f"Questions={'CUSTOM' if has_custom_question else 'DEFAULT'}, "
                f"Summary={'CUSTOM' if has_custom_summary else 'DEFAULT'}"
            )
            if has_custom_question:
                logger.info(f"   Custom Question Prompt (preview): {config.custom_question_prompt[:100]}...")
            if has_custom_summary:
                logger.info(f"   Custom Summary Prompt (preview): {config.custom_summary_prompt[:100]}...")
            
            # Step 1: Check for existing raw content or crawl blog
            logger.info(f"🔍 Checking for existing raw content: {normalized_url}")
            crawl_start = time.time()
            crawl_result = None
            blog_doc = None  # Store blog document for reuse
            
            # First, check if raw content already exists in database
            existing_blog = await self.storage.get_blog_by_url(normalized_url)
            
            if existing_blog:
                # Store blog document for later use (threshold check)
                blog_doc = existing_blog
                
                # Convert existing blog to CrawledContent format
                from fyi_widget_shared_library.models.schemas import CrawledContent
                
                blog_id = str(existing_blog["_id"])
                crawl_result = CrawledContent(
                    url=normalized_url,
                    title=existing_blog.get("title", ""),
                    content=existing_blog.get("content", ""),
                    language=existing_blog.get("language", "en"),
                    word_count=existing_blog.get("word_count", 0),
                    metadata=existing_blog.get("metadata", {})
                )
                
                # Validate existing content
                if not crawl_result.content or len(crawl_result.content.strip()) < 50:
                    logger.warning(f"⚠️  Existing content is invalid, will re-crawl: {normalized_url}")
                    crawl_result = None  # Force re-crawl
                    blog_doc = None  # Clear blog_doc since we'll re-crawl
                else:
                    crawl_duration = time.time() - crawl_start
                    crawl_operations_total.labels(publisher_domain=publisher_domain, status="cached").inc()
                    crawl_duration_seconds.labels(publisher_domain=publisher_domain).observe(crawl_duration)
                    crawl_content_size_bytes.labels(publisher_domain=publisher_domain).observe(len(crawl_result.content.encode('utf-8')))
                    crawl_word_count.labels(publisher_domain=publisher_domain).observe(crawl_result.word_count)
                    
                    logger.info(f"✅ Using existing raw content: {crawl_result.word_count} words (blog_id: {blog_id})")
            
            # If no existing content or invalid, crawl the blog
            if crawl_result is None:
                logger.info(f"🕷️  Crawling: {crawl_url}")
                try:
                    crawl_result = await self.crawler.crawl_url(crawl_url)
                    
                    # If we used a test URL for crawling, update the result URL to the original
                    if crawl_url != normalized_url:
                        crawl_result.url = normalized_url
                        logger.info(f"   Updated crawl result URL to original: {normalized_url}")
                    
                    # crawl_result is CrawledContent on success, exception raised on failure
                    if not crawl_result or not crawl_result.content:
                        raise Exception("Crawl failed: No content extracted")
                    
                    # Additional validation: check content quality
                    if len(crawl_result.content.strip()) < 50:
                        raise Exception(f"Crawl failed: Content too short ({len(crawl_result.content)} chars)")
                    
                    # Record crawl metrics
                    crawl_duration = time.time() - crawl_start
                    crawl_operations_total.labels(publisher_domain=publisher_domain, status="success").inc()
                    crawl_duration_seconds.labels(publisher_domain=publisher_domain).observe(crawl_duration)
                    crawl_content_size_bytes.labels(publisher_domain=publisher_domain).observe(len(crawl_result.content.encode('utf-8')))
                    crawl_word_count.labels(publisher_domain=publisher_domain).observe(crawl_result.word_count)
                    
                    logger.info(f"✅ Crawl successful: {crawl_result.word_count} words extracted")
                    
                    # Save raw blog content immediately after crawl succeeds
                    # This ensures content is preserved even if later processing steps fail
                    logger.info("💾 Saving raw blog content...")
                    db_start = time.time()
                    try:
                        blog_id = await self.storage.save_blog_content(
                            url=normalized_url,
                            title=crawl_result.title,  # Will be updated later if LLM generates a better title
                            content=crawl_result.content,
                            language=crawl_result.language,
                            word_count=crawl_result.word_count,
                            metadata=crawl_result.metadata
                        )
                        db_duration = time.time() - db_start
                        db_operations_total.labels(operation="save_blog", collection="raw_blog_content", status="success").inc()
                        db_operation_duration_seconds.labels(operation="save_blog", collection="raw_blog_content").observe(db_duration)
                        logger.info(f"✅ Raw blog content saved: {blog_id}")
                        
                        # Get the saved blog document for threshold check (single call)
                        blog_doc = await self.storage.get_blog_by_url(normalized_url)
                        if not blog_doc:
                            raise Exception("Blog document not found after save")
                    except Exception as save_error:
                        db_duration = time.time() - db_start
                        db_operations_total.labels(operation="save_blog", collection="raw_blog_content", status="error").inc()
                        db_operation_duration_seconds.labels(operation="save_blog", collection="raw_blog_content").observe(db_duration)
                        # Log but don't fail - we can try again later or the content might already exist
                        logger.warning(f"⚠️  Failed to save raw blog content: {save_error}. Continuing with processing...")
                        blog_id = None
                        blog_doc = None
                    
                except Exception as crawl_error:
                    # Record crawl failure
                    crawl_duration = time.time() - crawl_start
                    crawl_operations_total.labels(publisher_domain=publisher_domain, status="failed").inc()
                    crawl_duration_seconds.labels(publisher_domain=publisher_domain).observe(crawl_duration)
                    processing_errors_total.labels(publisher_domain=publisher_domain, error_type="crawl_error").inc()
                    logger.error(f"❌ Crawl failed for {normalized_url}: {crawl_error}")
                    raise Exception(f"Crawl failed: {str(crawl_error)}")
            
            # Ensure blog_id and blog_doc are available
            if blog_id is None or blog_doc is None:
                # Fallback: Try to get blog from database
                fallback_blog = await self.storage.get_blog_by_url(normalized_url)
                if fallback_blog:
                    blog_id = str(fallback_blog["_id"])
                    blog_doc = fallback_blog
                else:
                    raise Exception("Blog ID and document not available after crawl/save")
            
            # Threshold check: Check if we should process based on triggered_no_of_times
            logger.info("🔍 Checking processing threshold...")
            
            # Use the blog_doc we already have (no additional DB call)
            if not blog_doc:
                raise Exception("Blog document not found for threshold check")
            
            # Get triggered_count (default to 0 for backward compatibility with existing blogs)
            triggered_count = blog_doc.get("triggered_no_of_times", 0)
            threshold = config.threshold_before_processing_blog
            
            # If blog doesn't have triggered_no_of_times field yet, initialize it to 0
            # (will be incremented to 1 below)
            if "triggered_no_of_times" not in blog_doc:
                logger.info(f"📝 Initializing triggered_no_of_times for existing blog (was missing)")
                triggered_count = 0
            
            logger.info(f"📊 Threshold check: triggered_no_of_times={triggered_count}, threshold={threshold}")
            
            # Check: (triggered_no_of_times + 1) > threshold_before_processing_blog
            should_process = (triggered_count + 1) > threshold
            
            # Always increment triggered_no_of_times (whether processing or skipping)
            new_triggered_count = await self.storage.increment_triggered_count(blog_id)
            logger.info(f"📈 Incremented triggered_no_of_times: {triggered_count} → {new_triggered_count}")
            
            if not should_process:
                # Skip processing - threshold not met
                logger.info(
                    f"⏭️  Skipping processing: ({triggered_count} + 1) = {triggered_count + 1} is NOT > {threshold}. "
                    f"Blog needs {threshold + 1} triggers before processing."
                )
                
                # Mark job as skipped
                await self.job_repo.mark_job_skipped(
                    job_id=job.job_id,
                    error_message=f"Threshold not met: triggered_count ({triggered_count + 1}) <= threshold ({threshold})"
                )
                
                # Release blog slot (skipped is an end state like failed/completed)
                try:
                    publisher_id = job.publisher_id
                    if not publisher_id:
                        # Try to find publisher by domain
                        from urllib.parse import urlparse
                        parsed_url = urlparse(normalized_url)
                        domain = parsed_url.netloc
                        if domain.startswith('www.'):
                            domain = domain[4:]
                        db_publisher = await self.publisher_repo.get_publisher_by_domain(
                            domain.lower(), 
                            allow_subdomain=True
                        )
                        if db_publisher:
                            publisher_id = db_publisher.id
                    
                    if publisher_id:
                        await self.publisher_repo.release_blog_slot(
                            publisher_id,
                            processed=False,
                        )
                        logger.info(f"✅ Released blog slot for skipped job (publisher: {publisher_id})")
                except Exception as release_error:
                    logger.warning(f"⚠️  Failed to release reserved blog slot after skip: {release_error}")
                
                # Record metrics
                jobs_processed_total.labels(publisher_domain=publisher_domain, status="skipped").inc()
                jobs_processing_active.labels(publisher_domain=publisher_domain).dec()
                
                logger.info(f"✅ Job {job.job_id} skipped due to threshold check")
                return  # Exit early - job is done (skipped)
            
            # Threshold check passed - proceed with processing
            logger.info(
                f"✅ Threshold check passed: ({triggered_count} + 1) = {triggered_count + 1} > {threshold}. "
                f"Proceeding with processing..."
            )
            
            # Step 2: Generate summary (with custom prompt if available)
            prompt_type = "CUSTOM" if config.custom_summary_prompt else "DEFAULT"
            summary_model = get_model(config.summary_model)
            summary_model_label = summary_model or "default"
            
            # Log detailed model info for debugging
            logger.info(f"📝 Generating summary with {prompt_type} prompt:")
            logger.info(f"   Config summary_model (raw): {config.summary_model}")
            logger.info(f"   Extracted summary_model: {summary_model}")
            logger.info(f"   LLM Service instance model: {self.llm_service.model}")
            logger.info(f"   Will use model: {summary_model or self.llm_service.model}")
            logger.info(f"   Temperature: {config.summary_temperature}, max_tokens: {config.summary_max_tokens}")
            
            summary_start = time.time()
            try:
                summary_result = await self.llm_service.generate_summary(
                    content=crawl_result.content,
                    title=crawl_result.title,
                    custom_prompt=config.custom_summary_prompt,  # Fallback to default if None
                    model=summary_model,  # Use per-operation model (None will fall back to instance model)
                    temperature=config.summary_temperature,  # Use per-operation temperature
                    max_tokens=config.summary_max_tokens  # Use per-operation max_tokens
                )
                
                # Record LLM metrics
                summary_duration = time.time() - summary_start
                llm_operations_total.labels(
                    publisher_domain=publisher_domain,
                    operation="summary",
                    model=summary_model_label,
                    status="success"
                ).inc()
                llm_operation_duration_seconds.labels(
                    publisher_domain=publisher_domain,
                    operation="summary",
                    model=summary_model_label
                ).observe(summary_duration)
                
                # Record token usage if available
                summary_tokens = getattr(summary_result, "tokens_used", 0) or 0
                if summary_tokens:
                    llm_tokens_used_total.labels(
                        publisher_domain=publisher_domain,
                        operation="summary",
                        model=summary_model_label
                    ).inc(summary_tokens)
                
            except Exception as llm_error:
                summary_duration = time.time() - summary_start
                llm_operations_total.labels(
                    publisher_domain=publisher_domain,
                    operation="summary",
                    model=summary_model_label,
                    status="failed"
                ).inc()
                llm_operation_duration_seconds.labels(
                    publisher_domain=publisher_domain,
                    operation="summary",
                    model=summary_model_label
                ).observe(summary_duration)
                processing_errors_total.labels(publisher_domain=publisher_domain, error_type="llm_error").inc()
                raise
            
            # Parse summary (expecting JSON with title, summary, and key_points)
            llm_generated_title = None
            try:
                import json
                summary_data = json.loads(summary_result.text)
                llm_generated_title = summary_data.get("title", "").strip()
                summary_text = summary_data.get("summary", summary_result.text)
                key_points = summary_data.get("key_points", [])
                
                if llm_generated_title:
                    logger.info(f"✅ LLM generated title: {llm_generated_title[:80]}...")
                else:
                    logger.warning(f"⚠️  LLM summary response missing title field, falling back to crawled title")
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse summary JSON: {e}, using raw text")
                summary_text = summary_result.text
                key_points = []
            
            # Use LLM-generated title if available, otherwise fall back to crawled title
            final_title = llm_generated_title if llm_generated_title else crawl_result.title
            if final_title != crawl_result.title:
                logger.info(f"📝 Using LLM-generated title instead of crawled title")
            
            # Step 3: Generate questions (with custom prompt if available)
            prompt_type = "CUSTOM" if config.custom_question_prompt else "DEFAULT"
            questions_model = get_model(config.questions_model)
            questions_model_label = questions_model or "default"
            logger.info(f"❓ Generating {config.questions_per_blog} questions with {prompt_type} prompt (model: {questions_model}, temp: {config.questions_temperature}, max_tokens: {config.questions_max_tokens}, grounding: {config.use_grounding})...")
            
            questions_start = time.time()
            try:
                questions_result = await self.llm_service.generate_questions(
                    content=crawl_result.content,
                    title=crawl_result.title,
                    num_questions=config.questions_per_blog,
                    custom_prompt=config.custom_question_prompt,  # Fallback to default if None
                    model=questions_model,  # Use per-operation model
                    temperature=config.questions_temperature,  # Use per-operation temperature
                    max_tokens=config.questions_max_tokens,  # Use per-operation max_tokens
                    use_grounding=config.use_grounding  # Use grounding setting from publisher config
                )
                
                # Record LLM metrics
                questions_duration = time.time() - questions_start
                llm_operations_total.labels(
                    publisher_domain=publisher_domain,
                    operation="questions",
                    model=questions_model_label,
                    status="success"
                ).inc()
                llm_operation_duration_seconds.labels(
                    publisher_domain=publisher_domain,
                    operation="questions",
                    model=questions_model_label
                ).observe(questions_duration)
                
                # Record token usage if available
                question_tokens = getattr(questions_result, "tokens_used", 0) or 0
                if question_tokens:
                    llm_tokens_used_total.labels(
                        publisher_domain=publisher_domain,
                        operation="questions",
                        model=questions_model_label
                    ).inc(question_tokens)
                        
            except Exception as llm_error:
                questions_duration = time.time() - questions_start
                llm_operations_total.labels(
                    publisher_domain=publisher_domain,
                    operation="questions",
                    model=questions_model_label,
                    status="failed"
                ).inc()
                llm_operation_duration_seconds.labels(
                    publisher_domain=publisher_domain,
                    operation="questions",
                    model=questions_model_label
                ).observe(questions_duration)
                processing_errors_total.labels(publisher_domain=publisher_domain, error_type="llm_error").inc()
                raise
            
            # Parse questions (JSON format)
            questions = []
            filtered_count = 0
            try:
                import json
                import re
                
                # Clean the response - LLM might wrap JSON in markdown code blocks
                response_text = questions_result.text.strip()
                
                # Log full response at DEBUG level for debugging
                logger.debug(f"Raw LLM response (full): {response_text}")
                
                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    # Extract content between ```json and ``` or just ``` and ```
                    match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
                    if match:
                        response_text = match.group(1).strip()
                    else:
                        # Try removing just the first and last ```
                        lines = response_text.split('\n')
                        if lines[0].startswith('```'):
                            lines = lines[1:]
                        if lines and lines[-1].startswith('```'):
                            lines = lines[:-1]
                        response_text = '\n'.join(lines).strip()
                
                logger.debug(f"Cleaned JSON (first 500 chars): {response_text[:500]}...")
                
                questions_data = json.loads(response_text)
                questions_list = questions_data.get("questions", [])
                
                logger.info(f"📋 Parsing {len(questions_list)} questions from LLM response...")
                
                # Parse and validate each question
                for idx, q in enumerate(questions_list):
                    question_text = q.get("question", "")
                    answer_text = q.get("answer", "")
                    keyword_anchor = q.get("keyword_anchor", "")
                    probability = q.get("probability")
                    
                    # Check if question/answer are missing or empty
                    if not question_text or not answer_text:
                        filtered_count += 1
                        logger.warning(
                            f"⚠️  Question {idx + 1} filtered out (missing data): "
                            f"question={bool(question_text)}, answer={bool(answer_text)}. "
                            f"Raw data: {json.dumps(q)[:200]}"
                        )
                        continue
                    
                    # Additional validation: check for whitespace-only strings
                    if not question_text.strip() or not answer_text.strip():
                        filtered_count += 1
                        logger.warning(
                            f"⚠️  Question {idx + 1} filtered out (empty/whitespace): "
                            f"question_length={len(question_text.strip())}, answer_length={len(answer_text.strip())}"
                        )
                        continue
                    
                    questions.append((question_text.strip(), answer_text.strip(), keyword_anchor.strip() if keyword_anchor else "", probability))
                    logger.debug(f"✅ Question {idx + 1} parsed successfully: {question_text[:50]}... (anchor: {keyword_anchor}, prob: {probability})")
                
                valid_count = len(questions)
                logger.info(f"✅ Parsed {valid_count} valid questions from {len(questions_list)} total (filtered: {filtered_count})")
                
                # Take only the requested number if we have more
                if valid_count >= config.questions_per_blog:
                    questions = questions[:config.questions_per_blog]
                    logger.info(f"✅ Using first {config.questions_per_blog} valid questions")
                elif valid_count < config.questions_per_blog:
                    logger.warning(
                        f"⚠️  Only {valid_count}/{config.questions_per_blog} valid questions generated "
                        f"({filtered_count} filtered). Proceeding with available questions."
                    )
                        
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse JSON: {e}")
                logger.error(f"   Raw response (first 1000 chars): {response_text[:1000]}")
                raise ValueError(f"Question parsing failed: {e}. LLM response may be truncated or malformed.")
            except Exception as e:
                logger.error(f"❌ Unexpected error parsing questions: {e}")
                logger.error(f"   Raw response (first 500 chars): {questions_result.text[:500]}")
                raise ValueError(f"Question parsing failed: {e}. LLM response may be truncated or malformed.")
            
            # Final validation
            if len(questions) == 0:
                raise ValueError(f"No valid questions were generated. Expected {config.questions_per_blog} questions.")
            
            if len(questions) < config.questions_per_blog:
                logger.warning(
                    f"⚠️  Generated {len(questions)} questions instead of requested {config.questions_per_blog}. "
                    f"Proceeding with available questions."
                )
            
            # Step 4: Generate embeddings
            logger.info("🔢 Generating embeddings...")
            
            # Summary embedding
            embedding_model_label = "text-embedding-3-small"  # Default embedding model
            embedding_start = time.time()
            try:
                summary_embedding_result = await self.llm_service.generate_embedding(summary_text)
                embedding_duration = time.time() - embedding_start
                
                llm_operations_total.labels(
                    publisher_domain=publisher_domain,
                    operation="embedding",
                    model=embedding_model_label,
                    status="success"
                ).inc()
                llm_operation_duration_seconds.labels(
                    publisher_domain=publisher_domain,
                    operation="embedding",
                    model=embedding_model_label
                ).observe(embedding_duration)
                embeddings_generated_total.labels(publisher_domain=publisher_domain, type="summary").inc()
            except Exception as e:
                embedding_duration = time.time() - embedding_start
                llm_operations_total.labels(
                    publisher_domain=publisher_domain,
                    operation="embedding",
                    model=embedding_model_label,
                    status="failed"
                ).inc()
                processing_errors_total.labels(publisher_domain=publisher_domain, error_type="llm_error").inc()
                raise
            
            # Question embeddings
            question_embeddings = []
            for q_text, _, _, _ in questions:
                embedding_start = time.time()
                try:
                    emb_result = await self.llm_service.generate_embedding(q_text)
                    embedding_duration = time.time() - embedding_start
                    
                    llm_operations_total.labels(
                        publisher_domain=publisher_domain,
                        operation="embedding",
                        model=embedding_model_label,
                        status="success"
                    ).inc()
                    llm_operation_duration_seconds.labels(
                        publisher_domain=publisher_domain,
                        operation="embedding",
                        model=embedding_model_label
                    ).observe(embedding_duration)
                    embeddings_generated_total.labels(publisher_domain=publisher_domain, type="question").inc()
                    
                    question_embeddings.append(emb_result.embedding)
                except Exception as e:
                    embedding_duration = time.time() - embedding_start
                    llm_operations_total.labels(
                        publisher_domain=publisher_domain,
                        operation="embedding",
                        model=embedding_model_label,
                        status="failed"
                    ).inc()
                    processing_errors_total.labels(publisher_domain=publisher_domain, error_type="llm_error").inc()
                    raise
            
            # Step 5: Save to database
            logger.info("💾 Saving processed data to database...")
            
            # Raw blog content should already be saved after crawl (Step 1)
            # If it wasn't saved (e.g., due to error during save), try to save it now
            if blog_id is None:
                logger.warning("⚠️  Blog content not saved yet, attempting to save now...")
                db_start = time.time()
                try:
                    blog_id = await self.storage.save_blog_content(
                        url=normalized_url,
                        title=final_title,  # LLM-generated title or crawled title fallback
                        content=crawl_result.content,
                        language=crawl_result.language,
                        word_count=crawl_result.word_count,
                        metadata=crawl_result.metadata
                    )
                    db_duration = time.time() - db_start
                    db_operations_total.labels(operation="save_blog", collection="raw_blog_content", status="success").inc()
                    db_operation_duration_seconds.labels(operation="save_blog", collection="raw_blog_content").observe(db_duration)
                    logger.info(f"✅ Raw blog content saved: {blog_id}")
                except Exception as e:
                    db_duration = time.time() - db_start
                    db_operations_total.labels(operation="save_blog", collection="raw_blog_content", status="error").inc()
                    db_operation_duration_seconds.labels(operation="save_blog", collection="raw_blog_content").observe(db_duration)
                    processing_errors_total.labels(publisher_domain=publisher_domain, error_type="db_error").inc()
                    raise
            else:
                # Update title if LLM generated a better one
                if final_title != crawl_result.title:
                    logger.info(f"📝 LLM generated a better title, but raw content already saved. New title will be used for summary/questions only.")
            
            # Save summary (use normalized URL)
            # Pass LLM-generated title for storage (optional, stored for reference)
            db_start = time.time()
            try:
                summary_id = await self.storage.save_summary(
                    blog_id=blog_id,
                    blog_url=normalized_url,
                    summary_text=summary_text,
                    key_points=key_points,
                    embedding=summary_embedding_result.embedding,
                    title=llm_generated_title if llm_generated_title else None
                )
                db_duration = time.time() - db_start
                db_operations_total.labels(operation="save_summary", collection="blog_summaries", status="success").inc()
                db_operation_duration_seconds.labels(operation="save_summary", collection="blog_summaries").observe(db_duration)
            except Exception as e:
                db_duration = time.time() - db_start
                db_operations_total.labels(operation="save_summary", collection="blog_summaries", status="error").inc()
                db_operation_duration_seconds.labels(operation="save_summary", collection="blog_summaries").observe(db_duration)
                processing_errors_total.labels(publisher_domain=publisher_domain, error_type="db_error").inc()
                raise
            
            # Prepare questions for batch save
            questions_list = [
                {
                    "question": q_text,
                    "answer": a_text,
                    "keyword_anchor": keyword_anchor,
                    "probability": probability
                }
                for q_text, a_text, keyword_anchor, probability in questions
            ]
            
            # Save questions (use normalized URL)
            db_start = time.time()
            try:
                question_ids = await self.storage.save_questions(
                    blog_id=blog_id,
                    blog_url=normalized_url,
                    questions=questions_list,
                    embeddings=question_embeddings
                )
                db_duration = time.time() - db_start
                db_operations_total.labels(operation="save_questions", collection="questions", status="success").inc()
                db_operation_duration_seconds.labels(operation="save_questions", collection="questions").observe(db_duration)
            except Exception as e:
                db_duration = time.time() - db_start
                db_operations_total.labels(operation="save_questions", collection="questions", status="error").inc()
                db_operation_duration_seconds.labels(operation="save_questions", collection="questions").observe(db_duration)
                processing_errors_total.labels(publisher_domain=publisher_domain, error_type="db_error").inc()
                raise
            
            # Record questions generated metrics
            questions_generated_total.labels(publisher_domain=publisher_domain).inc(len(questions))
            questions_per_blog.labels(publisher_domain=publisher_domain).observe(len(questions))
            
            # Step 6: Mark job as completed
            processing_time = time.time() - start_time
            
            result = JobResult(
                summary_id=str(summary_id),
                question_count=len(questions),
                embedding_count=len(questions) + 1,
                processing_details={
                    "title": crawl_result.title,
                    "content_length": len(crawl_result.content),
                    "summary_length": len(summary_result.text)
                }
            )
            
            await self.job_repo.mark_job_completed(
                job_id=job.job_id,
                processing_time_seconds=processing_time,
                result=result.dict()
            )
            
            # Record job completion metrics
            jobs_processed_total.labels(publisher_domain=publisher_domain, status="success").inc()
            job_processing_duration_seconds.labels(publisher_domain=publisher_domain, status="success").observe(processing_time)
            jobs_processing_active.labels(publisher_domain=publisher_domain).dec()
            
            # Track publisher usage (blogs processed + questions generated)
            # Only count if this is the first time processing this blog URL
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(normalized_url)
                domain = parsed_url.netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Use subdomain matching to find publisher (e.g., info.contentretina.com -> contentretina.com)
                publisher = await self.publisher_repo.get_publisher_by_domain(domain, allow_subdomain=True)
                if publisher:
                    # Check if this blog was already processed before (to prevent double counting)
                    # Count completed jobs for this normalized URL (excluding current job)
                    existing_completed_jobs = await self.job_repo.collection.count_documents({
                        "blog_url": normalized_url,
                        "status": "completed",
                        "job_id": {"$ne": job.job_id}  # Exclude current job
                    })
                    
                    if existing_completed_jobs == 0:
                        processed_first_time = True
                    else:
                        processed_first_time = False
                        logger.info(
                            f"📊 Blog already processed previously ({existing_completed_jobs} previous jobs), skipping usage increment for {publisher.name}"
                        )

                    try:
                        publisher_id = job.publisher_id or (publisher.id if publisher else None)
                        if publisher_id:
                            await self.publisher_repo.release_blog_slot(
                                publisher_id,
                                processed=processed_first_time,
                                questions_generated=len(questions) if processed_first_time else 0,
                            )
                        if processed_first_time:
                            blogs_processed_total.labels(publisher_domain=publisher_domain).inc()
                            if publisher:
                                logger.info(
                                    f"📊 Usage tracked: +1 blog, +{len(questions)} questions for {publisher.name}"
                                )
                    except Exception as usage_error:
                        logger.warning(f"⚠️  Failed to record usage: {usage_error}")
            except Exception as usage_error:
                # Don't fail the job if usage tracking fails
                logger.warning(f"⚠️  Failed to track usage: {usage_error}")
            
            logger.info(f"✅ Job {job.job_id} completed in {processing_time:.2f}s")
            
        except Exception as e:
            # Mark job as failed
            error_msg = str(e)
            processing_time = time.time() - start_time
            error_type = "unknown"
            
            # Categorize error
            if "crawl" in error_msg.lower():
                error_type = "crawl_error"
            elif "llm" in error_msg.lower() or "openai" in error_msg.lower() or "anthropic" in error_msg.lower():
                error_type = "llm_error"
            elif "database" in error_msg.lower() or "mongodb" in error_msg.lower():
                error_type = "db_error"
            elif "validation" in error_msg.lower() or "parse" in error_msg.lower():
                error_type = "validation_error"
            
            # Record failure metrics
            jobs_processed_total.labels(publisher_domain=publisher_domain, status="failed").inc()
            job_processing_duration_seconds.labels(publisher_domain=publisher_domain, status="failed").observe(processing_time)
            jobs_processing_active.labels(publisher_domain=publisher_domain).dec()
            processing_errors_total.labels(publisher_domain=publisher_domain, error_type=error_type).inc()
            
            logger.error(f"❌ Job {job.job_id} failed: {error_msg}", exc_info=True)
            
            # Mark job as failed (may requeue if under max retries)
            await self.job_repo.mark_job_failed(
                job_id=job.job_id,
                error_message=error_msg,
                should_retry=True
            )
            
            # Check if job was permanently failed or requeued
            updated_job = await self.job_repo.get_job_by_id(job.job_id)
            if not updated_job:
                logger.error(f"❌ Job {job.job_id} not found after marking as failed - cannot determine status, keeping slot reserved for safety")
                return  # Keep slot reserved as fail-safe
            
            is_permanently_failed = updated_job.status == JobStatus.FAILED
            
            # Only release slot if job is permanently failed (not requeued)
            # If requeued, keep the slot reserved since the job will retry
            if is_permanently_failed:
                try:
                    if self.publisher_repo:
                        # Try to get publisher_id from job first (should be set by API now)
                        publisher_id = job.publisher_id
                        if not publisher_id and publisher:
                            publisher_id = publisher.id
                        if not publisher_id:
                            # Fallback: try to find publisher by domain (with subdomain matching)
                            db_publisher = await self.publisher_repo.get_publisher_by_domain(
                                publisher_domain, 
                                allow_subdomain=True
                            )
                            if db_publisher:
                                publisher_id = db_publisher.id
                                logger.info(f"📋 Found publisher by domain for slot release: {db_publisher.name} (domain: {db_publisher.domain})")
                        
                        if publisher_id:
                            await self.publisher_repo.release_blog_slot(
                                publisher_id,
                                processed=False,
                            )
                            logger.info(f"✅ Released blog slot for permanently failed job (publisher: {publisher_id})")
                        else:
                            logger.warning(f"⚠️  Could not find publisher_id to release blog slot (domain: {publisher_domain})")
                except Exception as release_error:
                    logger.warning(f"⚠️  Failed to release reserved blog slot after permanent failure: {release_error}")
            else:
                logger.info(f"🔄 Job {job.job_id} requeued for retry - keeping slot reserved")


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
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start worker
    worker = BlogProcessingWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt received")
    finally:
        await worker.stop()
        logger.info("👋 Worker shut down")


if __name__ == "__main__":
    asyncio.run(main())

