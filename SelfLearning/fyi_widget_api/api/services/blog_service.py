"""Service layer for blog processing operations."""

import logging
from datetime import datetime
from typing import Dict, Tuple
from fastapi import HTTPException

from fyi_widget_api.api.repositories import JobRepository, PublisherRepository
from fyi_widget_api.api.repositories.publisher_repository import UsageLimitExceededError
from fyi_widget_api.api.models.job_models import JobStatusResponse
from fyi_widget_api.api.models.publisher_models import Publisher
from fyi_widget_api.api.utils import normalize_url
from fyi_widget_api.api.services.publisher_service import PublisherService

logger = logging.getLogger(__name__)


class BlogService:
    """Blog service with constructor-injected dependencies."""

    def __init__(
        self,
        job_repo: JobRepository,
        publisher_repo: PublisherRepository,
    ):
        self.job_repo = job_repo
        self.publisher_repo = publisher_repo

    async def enqueue_blog_processing(
        self,
        *,
        blog_url: str,
        publisher: Publisher,
        request_id: str,
    ) -> Tuple[Dict, int, str]:
        """Enqueue or reuse a processing job for a blog URL."""
        normalized_url = normalize_url(blog_url)
        logger.info(f"[{request_id}] 📥 Enqueueing blog: {blog_url} (normalized: {normalized_url})")

        # Daily blog limit
        if publisher.config.daily_blog_limit:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            jobs_today = await self.job_repo.collection.count_documents(
                {
                    "blog_url": {"$regex": f"^https?://(www\\.)?{publisher.domain}"},
                    "status": "completed",
                    "completed_at": {"$gte": today_start},
                }
            )
            logger.info(f"📊 Daily usage: {jobs_today}/{publisher.config.daily_blog_limit}")
            if jobs_today >= publisher.config.daily_blog_limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily blog processing limit reached ({publisher.config.daily_blog_limit}). "
                    "Please try again tomorrow or upgrade your plan.",
                )

        # Existing blog check
        blogs_collection = self.job_repo.database["raw_blog_content"]
        existing_blog = await blogs_collection.find_one({"url": normalized_url})
        if existing_blog:
            logger.info(f"[{request_id}] ✅ Blog already exists: {blog_url}")
            existing_job = await self.job_repo.collection.find_one(
                {"blog_url": normalized_url, "status": "completed"}
            )
            if existing_job:
                logger.info(f"[{request_id}] ✅ Returning existing completed job: {existing_job['job_id']}")
                # Note: ProcessingJob is in worker service models, not needed here
                # We can work with the dict directly for status response
                job_response = JobStatusResponse(
                    job_id=existing_job.get("job_id"),
                    blog_url=existing_job.get("blog_url"),
                    status=existing_job.get("status"),
                    failure_count=existing_job.get("failure_count", 0),
                    error_message=existing_job.get("error_message"),
                    created_at=existing_job.get("created_at"),
                    started_at=existing_job.get("started_at"),
                    completed_at=existing_job.get("completed_at"),
                    processing_time_seconds=existing_job.get("processing_time_seconds"),
                    result=existing_job.get("result"),
                )
                return job_response.model_dump(), 200, "Blog already processed, returning existing job"

            logger.info(f"[{request_id}] ⚠️  Blog exists but no completed job found, will reprocess")

        # Enforce whitelist and limits, then enqueue
        PublisherService.ensure_url_whitelisted(normalized_url, publisher)

        slot_reserved = False
        try:
            if self.publisher_repo:
                await self.publisher_repo.reserve_blog_slot(publisher.id)
                slot_reserved = True

            job_id, is_new_job = await self.job_repo.create_job(
                blog_url=normalized_url,
                publisher_id=publisher.id,
                config=publisher.config.model_dump() if publisher.config else None,
            )
        except UsageLimitExceededError as exc:
            logger.warning(f"[{request_id}] ❌ Blog limit reached for publisher {publisher.id}: {exc}")
            raise HTTPException(status_code=403, detail=str(exc))
        except Exception:
            if slot_reserved and self.publisher_repo:
                try:
                    await self.publisher_repo.release_blog_slot(publisher.id, processed=False)
                except Exception as release_error:
                    logger.warning(f"[{request_id}] ⚠️ Failed to release reserved blog slot: {release_error}")
            raise

        # Get the created job to build response
        job_dict = await self.job_repo.get_job_by_id(job_id)
        if not job_dict:
            raise HTTPException(status_code=500, detail="Failed to retrieve created job")
        
        job_response = JobStatusResponse(
            job_id=job_dict.get("job_id"),
            blog_url=job_dict.get("blog_url"),
            status=job_dict.get("status"),
            failure_count=job_dict.get("failure_count", 0),
            error_message=job_dict.get("error_message"),
            created_at=job_dict.get("created_at"),
            started_at=job_dict.get("started_at"),
            completed_at=job_dict.get("completed_at"),
            processing_time_seconds=job_dict.get("processing_time_seconds"),
            result=job_dict.get("result"),
        )
        return job_response.model_dump(), 202, "Blog processing job enqueued successfully"

    async def get_job_status(self, *, job_id: str, request_id: str) -> Dict:
        """Return job status."""
        job = await self.job_repo.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        job_response = JobStatusResponse(
            job_id=job.get("job_id"),
            blog_url=job.get("blog_url"),
            status=job.get("status"),
            failure_count=job.get("failure_count", 0),
            error_message=job.get("error_message"),
            created_at=job.get("created_at"),
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at"),
            processing_time_seconds=job.get("processing_time_seconds"),
            result=job.get("result"),
            updated_at=job.get("updated_at"),
        )
        result_data = job_response.model_dump()
        for field in ["created_at", "started_at", "completed_at", "updated_at"]:
            if field in result_data and result_data[field] and hasattr(result_data[field], "isoformat"):
                result_data[field] = result_data[field].isoformat()
        return result_data

    async def get_queue_stats(self) -> Dict:
        """Return aggregate queue stats."""
        stats = await self.job_repo.get_job_stats()
        return {"queue_stats": stats, "total_jobs": sum(stats.values())}

    async def cancel_job(self, *, job_id: str, request_id: str) -> Dict:
        """Cancel a queued job."""
        success = await self.job_repo.cancel_job(job_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Job cannot be cancelled (may already be processing or completed)",
            )
        return {"job_id": job_id, "cancelled": True}

