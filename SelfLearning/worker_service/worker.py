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

from shared.data import JobRepository, DatabaseManager
from shared.data.postgres_database import PostgresPublisherRepository
from shared.models import ProcessingJob, JobStatus, JobResult
from shared.models.publisher import PublisherConfig
from shared.services import CrawlerService, LLMService, StorageService
from shared.utils import normalize_url

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
        self.crawler = CrawlerService()
        self.llm_service = LLMService(api_key=OPENAI_API_KEY)
        self.storage = StorageService(database=self.db_manager.database)
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
            logger.info(f"📋 Config: {config.questions_per_blog} questions, model: {config.llm_model}")
            
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
            crawl_result = await self.crawler.crawl_url(normalized_url)
            
            # crawl_result is CrawledContent on success, exception raised on failure
            if not crawl_result or not crawl_result.content:
                raise Exception("Crawl failed: No content extracted")
            
            # Step 2: Generate summary (with custom prompt if available)
            prompt_type = "CUSTOM" if config.custom_summary_prompt else "DEFAULT"
            logger.info(f"📝 Generating summary with {prompt_type} prompt...")
            summary_result = await self.llm_service.generate_summary(
                content=crawl_result.content,
                title=crawl_result.title,
                custom_prompt=config.custom_summary_prompt  # Fallback to default if None
            )
            
            # Parse summary (expecting JSON with summary and key_points)
            try:
                import json
                summary_data = json.loads(summary_result.text)
                summary_text = summary_data.get("summary", summary_result.text)
                key_points = summary_data.get("key_points", [])
            except:
                summary_text = summary_result.text
                key_points = []
            
            # Step 3: Generate questions (with custom prompt if available)
            prompt_type = "CUSTOM" if config.custom_question_prompt else "DEFAULT"
            logger.info(f"❓ Generating {config.questions_per_blog} questions with {prompt_type} prompt...")
            questions_result = await self.llm_service.generate_questions(
                content=crawl_result.content,
                title=crawl_result.title,
                num_questions=config.questions_per_blog,
                custom_prompt=config.custom_question_prompt  # Fallback to default if None
            )
            
            # Parse questions (JSON format)
            questions = []
            try:
                import json
                import re
                
                # Clean the response - LLM might wrap JSON in markdown code blocks
                response_text = questions_result.text.strip()
                
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
                
                logger.debug(f"Parsing JSON from: {response_text[:200]}...")
                
                questions_data = json.loads(response_text)
                questions_list = questions_data.get("questions", [])
                
                for q in questions_list:
                    question_text = q.get("question", "")
                    answer_text = q.get("answer", "")
                    if question_text and answer_text:
                        questions.append((question_text, answer_text))
                
                logger.info(f"✅ Parsed {len(questions)} questions")
            except Exception as e:
                logger.error(f"❌ Failed to parse questions JSON: {e}")
                logger.error(f"   Raw response: {questions_result.text[:500]}")
                raise ValueError(f"Question parsing failed: {e}. LLM response may be truncated or malformed.")
            
            # Validate that questions were actually generated
            if len(questions) == 0:
                raise ValueError(f"No questions were generated. Expected {config.questions_per_blog} questions.")
            
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
            blog_id = await self.storage.save_blog_content(
                url=normalized_url,
                title=crawl_result.title,
                content=crawl_result.content,
                language=crawl_result.language,
                word_count=crawl_result.word_count,
                metadata=crawl_result.metadata
            )
            
            # Save summary (use normalized URL)
            summary_id = await self.storage.save_summary(
                blog_id=blog_id,
                blog_url=normalized_url,
                summary_text=summary_text,
                key_points=key_points,
                embedding=summary_embedding_result.embedding
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
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(normalized_url)
                domain = parsed_url.netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                publisher = await self.publisher_repo.get_publisher_by_domain(domain)
                if publisher:
                    await self.publisher_repo.increment_usage(
                        publisher.id,
                        blogs_processed=1,
                        questions_generated=len(questions)
                    )
                    logger.info(f"📊 Usage tracked: +1 blog, +{len(questions)} questions for {publisher.name}")
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

