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
from fyi_widget_shared_library.utils import normalize_url

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
            
            # Fetch publisher
            publisher = await self.publisher_repo.get_publisher_by_domain(domain)
            
            if publisher:
                logger.info(f"✅ Using config for publisher: {publisher.name}")
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
        
        while self.running:
            try:
                # Get next job
                job = await self.job_repo.get_next_queued_job()
                
                if job:
                    logger.info(f"📥 Found job: {job.job_id} ({job.blog_url})")
                    await self.process_job(job)
                else:
                    # No jobs, wait before next poll
                    await asyncio.sleep(POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"❌ Error in poll loop: {e}", exc_info=True)
                await asyncio.sleep(POLL_INTERVAL)
    
    async def process_job(self, job: ProcessingJob):
        """
        Process a single job.
        
        Args:
            job: Job to process
        """
        start_time = time.time()
        
        try:
            # Mark as processing
            success = await self.job_repo.mark_job_processing(job.job_id)
            if not success:
                logger.warning(f"⚠️  Could not lock job {job.job_id}, skipping")
                return
            
            logger.info(f"🔄 Processing job {job.job_id}...")
            
            # Normalize URL before processing
            normalized_url = normalize_url(job.blog_url)
            if normalized_url != job.blog_url:
                logger.info(f"   Normalized URL: {normalized_url}")
            
            # Fetch publisher config
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
            
            # Step 1: Crawl blog
            logger.info(f"🕷️  Crawling: {normalized_url}")
            try:
                crawl_result = await self.crawler.crawl_url(normalized_url)
                
                # crawl_result is CrawledContent on success, exception raised on failure
                if not crawl_result or not crawl_result.content:
                    raise Exception("Crawl failed: No content extracted")
                
                # Additional validation: check content quality
                if len(crawl_result.content.strip()) < 50:
                    raise Exception(f"Crawl failed: Content too short ({len(crawl_result.content)} chars)")
                
                logger.info(f"✅ Crawl successful: {crawl_result.word_count} words extracted")
                
            except Exception as crawl_error:
                logger.error(f"❌ Crawl failed for {normalized_url}: {crawl_error}")
                raise Exception(f"Crawl failed: {str(crawl_error)}")
            
            # Step 2: Generate summary (with custom prompt if available)
            prompt_type = "CUSTOM" if config.custom_summary_prompt else "DEFAULT"
            summary_model = get_model(config.summary_model)
            logger.info(f"📝 Generating summary with {prompt_type} prompt (model: {summary_model}, temp: {config.summary_temperature}, max_tokens: {config.summary_max_tokens})...")
            summary_result = await self.llm_service.generate_summary(
                content=crawl_result.content,
                title=crawl_result.title,
                custom_prompt=config.custom_summary_prompt,  # Fallback to default if None
                model=summary_model,  # Use per-operation model
                temperature=config.summary_temperature,  # Use per-operation temperature
                max_tokens=config.summary_max_tokens  # Use per-operation max_tokens
            )
            
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
            logger.info(f"❓ Generating {config.questions_per_blog} questions with {prompt_type} prompt (model: {questions_model}, temp: {config.questions_temperature}, max_tokens: {config.questions_max_tokens})...")
            
            questions_result = await self.llm_service.generate_questions(
                content=crawl_result.content,
                title=crawl_result.title,
                num_questions=config.questions_per_blog,
                custom_prompt=config.custom_question_prompt,  # Fallback to default if None
                model=questions_model,  # Use per-operation model
                temperature=config.questions_temperature,  # Use per-operation temperature
                max_tokens=config.questions_max_tokens  # Use per-operation max_tokens
            )
            
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
                    
                    questions.append((question_text.strip(), answer_text.strip()))
                    logger.debug(f"✅ Question {idx + 1} parsed successfully: {question_text[:50]}...")
                
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
            summary_embedding_result = await self.llm_service.generate_embedding(
                summary_text
            )
            
            # Question embeddings
            question_embeddings = []
            for q_text, _ in questions:
                emb_result = await self.llm_service.generate_embedding(q_text)
                question_embeddings.append(emb_result.embedding)
            
            # Step 5: Save to database
            logger.info("💾 Saving to database...")
            
            # Save raw blog content (use normalized URL)
            # Use LLM-generated title if available, otherwise use crawled title
            blog_id = await self.storage.save_blog_content(
                url=normalized_url,
                title=final_title,  # LLM-generated title or crawled title fallback
                content=crawl_result.content,
                language=crawl_result.language,
                word_count=crawl_result.word_count,
                metadata=crawl_result.metadata
            )
            
            # Save summary (use normalized URL)
            # Pass LLM-generated title for storage (optional, stored for reference)
            summary_id = await self.storage.save_summary(
                blog_id=blog_id,
                blog_url=normalized_url,
                summary_text=summary_text,
                key_points=key_points,
                embedding=summary_embedding_result.embedding,
                title=llm_generated_title if llm_generated_title else None
            )
            
            # Prepare questions for batch save
            questions_list = [
                {"question": q_text, "answer": a_text, "icon": "💡"}
                for q_text, a_text in questions
            ]
            
            # Save questions (use normalized URL)
            question_ids = await self.storage.save_questions(
                blog_id=blog_id,
                blog_url=normalized_url,
                questions=questions_list,
                embeddings=question_embeddings
            )
            
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
            
            # Track publisher usage (blogs processed + questions generated)
            # Only count if this is the first time processing this blog URL
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(normalized_url)
                domain = parsed_url.netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                publisher = await self.publisher_repo.get_publisher_by_domain(domain)
                if publisher:
                    # Check if this blog was already processed before (to prevent double counting)
                    # Count completed jobs for this normalized URL (excluding current job)
                    existing_completed_jobs = await self.job_repo.collection.count_documents({
                        "blog_url": normalized_url,
                        "status": "completed",
                        "job_id": {"$ne": job.job_id}  # Exclude current job
                    })
                    
                    if existing_completed_jobs == 0:
                        # First time processing this blog - increment counter
                        await self.publisher_repo.increment_usage(
                            publisher.id,
                            blogs_processed=1,
                            questions_generated=len(questions)
                        )
                        logger.info(f"📊 Usage tracked: +1 blog, +{len(questions)} questions for {publisher.name}")
                    else:
                        # Blog was already processed before - don't count again
                        logger.info(f"📊 Blog already processed previously ({existing_completed_jobs} previous jobs), skipping usage increment for {publisher.name}")
            except Exception as usage_error:
                # Don't fail the job if usage tracking fails
                logger.warning(f"⚠️  Failed to track usage: {usage_error}")
            
            logger.info(f"✅ Job {job.job_id} completed in {processing_time:.2f}s")
            
        except Exception as e:
            # Mark job as failed
            error_msg = str(e)
            logger.error(f"❌ Job {job.job_id} failed: {error_msg}", exc_info=True)
            
            await self.job_repo.mark_job_failed(
                job_id=job.job_id,
                error_message=error_msg,
                should_retry=True
            )


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

