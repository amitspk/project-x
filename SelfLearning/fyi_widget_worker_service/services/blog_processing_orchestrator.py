"""Orchestrator for blog processing pipeline."""

import logging
import time
from typing import Optional

from fyi_widget_worker_service.repositories import JobRepository, PublisherRepository
from fyi_widget_worker_service.models.job_models import ProcessingJob, JobStatus, JobResult
from fyi_widget_worker_service.models.publisher_models import PublisherConfig
from fyi_widget_worker_service.services.blog_content_repository import BlogContentRepository
from fyi_widget_worker_service.utils import normalize_url, extract_domain

from .content_retrieval_service import ContentRetrievalService
from .threshold_service import ThresholdService
from .llm_generation_service import LLMGenerationService

from fyi_widget_worker_service.core.metrics import (
    jobs_processing_active,
    jobs_processed_total,
    job_processing_duration_seconds,
    questions_generated_total,
    questions_per_blog,
    blogs_processed_total,
    processing_errors_total,
    db_operations_total,
    db_operation_duration_seconds,
)

logger = logging.getLogger(__name__)


class BlogProcessingOrchestrator:
    """Orchestrates the blog processing pipeline using specialized services."""
    
    def __init__(
        self,
        job_repo: JobRepository,
        publisher_repo: PublisherRepository,
        storage: BlogContentRepository,
        content_retrieval_service: ContentRetrievalService,
        threshold_service: ThresholdService,
        llm_generation_service: LLMGenerationService,
    ):
        """
        Initialize orchestrator with all required services.
        
        Args:
            job_repo: Job repository
            publisher_repo: Publisher repository
            storage: Storage service
            content_retrieval_service: Content retrieval service
            threshold_service: Threshold checking service
            llm_generation_service: LLM generation service
        """
        self.job_repo = job_repo
        self.publisher_repo = publisher_repo
        self.storage = storage
        self.content_retrieval_service = content_retrieval_service
        self.threshold_service = threshold_service
        self.llm_generation_service = llm_generation_service
    
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
            domain = extract_domain(blog_url)
            publisher = await self.publisher_repo.get_publisher_by_domain(domain, allow_subdomain=True)
            
            if publisher:
                logger.info(f"✅ Using config for publisher: {publisher.name} (domain: {publisher.domain}) - matched from blog URL domain: {domain}")
                return publisher.config
            else:
                logger.warning(f"⚠️  Publisher not found for domain: {domain}, using defaults")
                return PublisherConfig()
        except Exception as e:
            logger.warning(f"⚠️  Failed to fetch publisher config: {e}, using defaults")
            return PublisherConfig()
    
    async def process_job(self, job: ProcessingJob) -> None:
        """
        Process a single job through the complete pipeline.
        
        Args:
            job: Job to process
        """
        start_time = time.time()
        publisher_domain = extract_domain(job.blog_url)
        
        try:
            # Job is already locked atomically by get_next_queued_job()
            # No need to call mark_job_processing() separately
            logger.info(f"🔄 Processing job {job.job_id}...")
            jobs_processing_active.labels(publisher_domain=publisher_domain).inc()
            
            # Normalize URL
            normalized_url = normalize_url(job.blog_url)
            if normalized_url != job.blog_url:
                logger.info(f"   Normalized URL: {normalized_url}")
            
            # Fetch publisher config
            config = await self.get_publisher_config(normalized_url)
            logger.info(f"📋 Config: {config.questions_per_blog} questions")
            
            # Log prompt configuration
            has_custom_question = config.custom_question_prompt is not None
            has_custom_summary = config.custom_summary_prompt is not None
            logger.info(
                f"🎯 Prompts: "
                f"Questions={'CUSTOM' if has_custom_question else 'DEFAULT'}, "
                f"Summary={'CUSTOM' if has_custom_summary else 'DEFAULT'}"
            )
            
            # Step 1: Get blog content (from cache or crawl)
            crawl_result, blog_id, blog_doc = await self.content_retrieval_service.get_blog_content(
                url=normalized_url,
                publisher_domain=publisher_domain
            )
            
            # Step 2: Check threshold
            should_process, _ = await self.threshold_service.should_process_blog(
                blog_id=blog_id,
                blog_doc=blog_doc,
                config=config,
                job_id=job.job_id
            )
            
            if not should_process:
                # Job was skipped due to threshold
                jobs_processed_total.labels(publisher_domain=publisher_domain, status="skipped").inc()
                jobs_processing_active.labels(publisher_domain=publisher_domain).dec()
                
                # Release blog slot for skipped job
                await self._release_blog_slot(job, normalized_url, publisher_domain, processed=False)
                return
            
            # Step 3: Generate LLM content (summary, questions, embeddings)
            summary_text, key_points, llm_generated_title = await self.llm_generation_service.generate_summary(
                crawl_result=crawl_result,
                config=config,
                publisher_domain=publisher_domain
            )
            
            questions = await self.llm_generation_service.generate_questions(
                crawl_result=crawl_result,
                config=config,
                publisher_domain=publisher_domain
            )
            
            summary_embedding, question_embeddings = await self.llm_generation_service.generate_embeddings(
                summary_text=summary_text,
                questions=questions,
                publisher_domain=publisher_domain
            )
            
            # Determine final title
            final_title = llm_generated_title if llm_generated_title else crawl_result.title
            if final_title != crawl_result.title:
                logger.info(f"📝 Using LLM-generated title instead of crawled title")
            
            # Step 4: Save results to database
            summary_id = await self._save_processing_results(
                normalized_url=normalized_url,
                blog_id=blog_id,
                final_title=final_title,
                summary_text=summary_text,
                key_points=key_points,
                llm_generated_title=llm_generated_title,
                summary_embedding=summary_embedding,
                questions=questions,
                question_embeddings=question_embeddings,
                publisher_domain=publisher_domain
            )
            
            # Step 5: Mark job as completed
            processing_time = time.time() - start_time
            result = JobResult(
                summary_id=str(summary_id),
                question_count=len(questions),
                embedding_count=len(questions) + 1,
                processing_details={
                    "title": crawl_result.title,
                    "content_length": len(crawl_result.content),
                    "summary_length": len(summary_text)
                }
            )
            
            await self.job_repo.mark_job_completed(
                job_id=job.job_id,
                processing_time_seconds=processing_time,
                result=result.dict()
            )
            
            # Record metrics
            jobs_processed_total.labels(publisher_domain=publisher_domain, status="success").inc()
            job_processing_duration_seconds.labels(publisher_domain=publisher_domain, status="success").observe(processing_time)
            jobs_processing_active.labels(publisher_domain=publisher_domain).dec()
            questions_generated_total.labels(publisher_domain=publisher_domain).inc(len(questions))
            questions_per_blog.labels(publisher_domain=publisher_domain).observe(len(questions))
            
            # Step 6: Track publisher usage
            await self._track_publisher_usage(job, normalized_url, publisher_domain, questions)
            
            logger.info(f"✅ Job {job.job_id} completed in {processing_time:.2f}s")
            
        except Exception as e:
            # Handle job failure
            await self._handle_job_failure(job, publisher_domain, start_time, e)
    
    async def _save_processing_results(
        self,
        normalized_url: str,
        blog_id: str,
        final_title: str,
        summary_text: str,
        key_points: list,
        llm_generated_title: Optional[str],
        summary_embedding: list,
        questions: list,
        question_embeddings: list,
        publisher_domain: str,
    ) -> str:
        """Save all processing results to database."""
        logger.info("💾 Saving processed data to database...")
        
        # Save summary
        db_start = time.time()
        try:
            summary_id = await self.storage.save_summary(
                blog_id=blog_id,
                blog_url=normalized_url,
                summary_text=summary_text,
                key_points=key_points,
                embedding=summary_embedding,
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
        
        # Save questions
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
        
        return summary_id
    
    async def _track_publisher_usage(
        self,
        job: ProcessingJob,
        normalized_url: str,
        publisher_domain: str,
        questions: list,
    ) -> None:
        """Track publisher usage (blogs processed + questions generated)."""
        try:
            domain = extract_domain(normalized_url)
            publisher = await self.publisher_repo.get_publisher_by_domain(domain, allow_subdomain=True)
            
            if publisher:
                # Check if this blog was already processed before (to prevent double counting)
                existing_completed_jobs = await self.job_repo.collection.count_documents({
                    "blog_url": normalized_url,
                    "status": "completed",
                    "job_id": {"$ne": job.job_id}
                })
                
                processed_first_time = existing_completed_jobs == 0
                if not processed_first_time:
                    logger.info(
                        f"📊 Blog already processed previously ({existing_completed_jobs} previous jobs), "
                        f"skipping usage increment for {publisher.name}"
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
                        logger.info(f"📊 Usage tracked: +1 blog, +{len(questions)} questions for {publisher.name}")
                except Exception as usage_error:
                    logger.warning(f"⚠️  Failed to record usage: {usage_error}")
        except Exception as usage_error:
            logger.warning(f"⚠️  Failed to track usage: {usage_error}")
    
    async def _release_blog_slot(
        self,
        job: ProcessingJob,
        normalized_url: str,
        publisher_domain: str,
        processed: bool,
    ) -> None:
        """Release blog slot for publisher."""
        try:
            publisher_id = job.publisher_id
            if not publisher_id:
                domain = extract_domain(normalized_url)
                publisher = await self.publisher_repo.get_publisher_by_domain(domain, allow_subdomain=True)
                if publisher:
                    publisher_id = publisher.id
            
            if publisher_id:
                await self.publisher_repo.release_blog_slot(publisher_id, processed=processed)
                logger.info(f"✅ Released blog slot (publisher: {publisher_id}, processed: {processed})")
        except Exception as release_error:
            logger.warning(f"⚠️  Failed to release blog slot: {release_error}")
    
    async def _handle_job_failure(
        self,
        job: ProcessingJob,
        publisher_domain: str,
        start_time: float,
        error: Exception,
    ) -> None:
        """Handle job failure: categorize error, mark job, release slot if needed."""
        error_msg = str(error)
        processing_time = time.time() - start_time
        error_type = "unknown"
        
        # Categorize error
        error_lower = error_msg.lower()
        if "crawl" in error_lower:
            error_type = "crawl_error"
        elif "llm" in error_lower or "openai" in error_lower or "anthropic" in error_lower:
            error_type = "llm_error"
        elif "database" in error_lower or "mongodb" in error_lower:
            error_type = "db_error"
        elif "validation" in error_lower or "parse" in error_lower:
            error_type = "validation_error"
        
        # Record failure metrics
        jobs_processed_total.labels(publisher_domain=publisher_domain, status="failed").inc()
        job_processing_duration_seconds.labels(publisher_domain=publisher_domain, status="failed").observe(processing_time)
        jobs_processing_active.labels(publisher_domain=publisher_domain).dec()
        processing_errors_total.labels(publisher_domain=publisher_domain, error_type=error_type).inc()
        
        logger.error(f"❌ Job {job.job_id} failed: {error_msg}", exc_info=True)
        
        # Mark job as failed
        await self.job_repo.mark_job_failed(
            job_id=job.job_id,
            error_message=error_msg,
            should_retry=True
        )
        
        # Check if job was permanently failed or requeued
        updated_job = await self.job_repo.get_job_by_id(job.job_id)
        if not updated_job:
            logger.error(f"❌ Job {job.job_id} not found after marking as failed - keeping slot reserved for safety")
            return
        
        is_permanently_failed = updated_job.status == JobStatus.FAILED
        
        # Only release slot if job is permanently failed (not requeued)
        if is_permanently_failed:
            await self._release_blog_slot(job, job.blog_url, publisher_domain, processed=False)
        else:
            logger.info(f"🔄 Job {job.job_id} requeued for retry - keeping slot reserved")

