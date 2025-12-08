"""Repository for job queue operations."""

import logging
from datetime import datetime
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, IndexModel

from ..models.job_queue import ProcessingJob, JobStatus

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository for managing processing jobs."""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """Initialize repository with database connection."""
        self.database = database
        self.collection: AsyncIOMotorCollection = database["processing_jobs"]
        logger.info("✅ JobRepository initialized")
    
    async def create_indexes(self):
        """Create indexes for efficient querying."""
        try:
            indexes = [
                IndexModel([("status", ASCENDING), ("created_at", ASCENDING)]),
                IndexModel([("blog_url", ASCENDING)]),
                IndexModel([("job_id", ASCENDING)], unique=True),
            ]
            await self.collection.create_indexes(indexes)
            logger.info("✅ Job queue indexes created")
        except Exception as e:
            logger.warning(f"⚠️  Index creation warning: {e}")
    
    async def create_job(
        self,
        blog_url: str,
        publisher_id: Optional[str] = None,
        config: Optional[dict] = None
    ) -> tuple[str, bool]:
        """
        Create a new processing job with publisher context.
        
        Args:
            blog_url: URL of the blog to process
            publisher_id: ID of the publisher creating the job
            config: Publisher configuration for processing
            
        Returns:
            Tuple of (job_id: str, is_new_job: bool)
            - job_id: The job ID (existing or newly created)
            - is_new_job: True if a new job was created, False if an existing job was returned
        """
        # Check if URL is already queued or processing
        # Allow immediate requeuing of skipped jobs, but prevent duplicate QUEUED/PROCESSING jobs
        existing = await self.collection.find_one({
            "blog_url": blog_url,
            "status": {"$in": [JobStatus.QUEUED.value, JobStatus.PROCESSING.value]}
        })
        
        if existing:
            logger.info(f"📋 Job already queued/processing for URL: {blog_url}")
            return existing.get("job_id"), False
        
        # Create new job
        job = ProcessingJob(
            blog_url=blog_url,
            publisher_id=publisher_id,
            config=config
        )
        job_dict = job.dict()
        
        await self.collection.insert_one(job_dict)
        logger.info(f"✅ Created job {job.job_id} for URL: {blog_url} (Publisher: {publisher_id})")
        
        return job.job_id, True
    
    async def enqueue_job(
        self, 
        blog_url: str,
        publisher_id: Optional[str] = None,
        config: Optional[dict] = None
    ) -> ProcessingJob:
        """
        Enqueue a new processing job.
        
        Args:
            blog_url: URL of the blog to process
            publisher_id: ID of the publisher creating the job (optional)
            config: Publisher configuration for processing (optional)
            
        Returns:
            Created ProcessingJob
        """
        # Check if URL is already queued or processing
        existing = await self.collection.find_one({
            "blog_url": blog_url,
            "status": {"$in": [JobStatus.QUEUED.value, JobStatus.PROCESSING.value]}
        })
        
        if existing:
            logger.info(f"📋 Job already queued/processing for URL: {blog_url}")
            return ProcessingJob(**existing)
        
        # Create new job with publisher context
        job = ProcessingJob(
            blog_url=blog_url,
            publisher_id=publisher_id,
            config=config
        )
        job_dict = job.dict()
        
        await self.collection.insert_one(job_dict)
        logger.info(f"✅ Enqueued job {job.job_id} for URL: {blog_url} (Publisher: {publisher_id})")
        
        return job
    
    async def get_job_by_id(self, job_id: str) -> Optional[ProcessingJob]:
        """Get job by job_id."""
        job_dict = await self.collection.find_one({"job_id": job_id})
        if job_dict:
            return ProcessingJob(**job_dict)
        return None
    
    async def get_next_queued_job(self) -> Optional[ProcessingJob]:
        """
        Get the next queued job (oldest first).
        
        Returns:
            ProcessingJob or None if queue is empty
        """
        job_dict = await self.collection.find_one(
            {"status": JobStatus.QUEUED.value},
            sort=[("created_at", ASCENDING)]
        )
        
        if job_dict:
            return ProcessingJob(**job_dict)
        return None
    
    async def mark_job_processing(self, job_id: str) -> bool:
        """
        Mark a job as processing.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if successfully updated
        """
        result = await self.collection.update_one(
            {"job_id": job_id, "status": JobStatus.QUEUED.value},
            {
                "$set": {
                    "status": JobStatus.PROCESSING.value,
                    "started_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"🔄 Job {job_id} marked as processing")
            return True
        else:
            logger.warning(f"⚠️  Could not mark job {job_id} as processing (may have been picked up by another worker)")
            return False
    
    async def mark_job_completed(
        self,
        job_id: str,
        processing_time_seconds: float,
        result: dict
    ) -> bool:
        """
        Mark a job as completed.
        
        Args:
            job_id: Job ID
            processing_time_seconds: Time taken to process
            result: Processing result
            
        Returns:
            True if successfully updated
        """
        update_result = await self.collection.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": JobStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "processing_time_seconds": processing_time_seconds,
                    "result": result
                }
            }
        )
        
        if update_result.modified_count > 0:
            logger.info(f"✅ Job {job_id} marked as completed ({processing_time_seconds:.2f}s)")
            return True
        return False
    
    async def mark_job_failed(
        self,
        job_id: str,
        error_message: str,
        should_retry: bool = True
    ) -> bool:
        """
        Mark a job as failed and optionally requeue for retry.
        
        Args:
            job_id: Job ID
            error_message: Error message
            should_retry: If True, increment failure_count and requeue if under max_retries
            
        Returns:
            True if successfully updated
        """
        # Get current job
        job = await self.get_job_by_id(job_id)
        if not job:
            logger.error(f"❌ Job {job_id} not found")
            return False
        
        new_failure_count = job.failure_count + 1
        
        # Determine new status
        if should_retry and new_failure_count < job.max_retries:
            new_status = JobStatus.QUEUED.value
            logger.warning(f"⚠️  Job {job_id} failed (attempt {new_failure_count}/{job.max_retries}), requeuing...")
        else:
            new_status = JobStatus.FAILED.value
            logger.error(f"❌ Job {job_id} failed permanently after {new_failure_count} attempts")
        
        # Update job
        update_result = await self.collection.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": new_status,
                    "failure_count": new_failure_count,
                    "error_message": error_message,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return update_result.modified_count > 0
    
    async def mark_job_skipped(
        self,
        job_id: str,
        error_message: str = "Job skipped due to threshold check"
    ) -> bool:
        """
        Mark a job as skipped.
        
        Args:
            job_id: Job ID
            error_message: Reason for skipping
            
        Returns:
            True if successfully updated
        """
        update_result = await self.collection.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": JobStatus.SKIPPED.value,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "error_message": error_message
                }
            }
        )
        
        if update_result.modified_count > 0:
            logger.info(f"⏭️  Job {job_id} marked as skipped: {error_message}")
            return True
        return False
    
    async def get_job_stats(self) -> dict:
        """Get statistics about jobs in the queue."""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=None)
        
        stats = {status.value: 0 for status in JobStatus}
        for result in results:
            stats[result["_id"]] = result["count"]
        
        return stats
    
    async def get_failed_jobs(self, limit: int = 10) -> List[ProcessingJob]:
        """Get recently failed jobs."""
        cursor = self.collection.find(
            {"status": JobStatus.FAILED.value}
        ).sort("updated_at", -1).limit(limit)
        
        jobs = []
        async for job_dict in cursor:
            jobs.append(ProcessingJob(**job_dict))
        
        return jobs
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job."""
        result = await self.collection.update_one(
            {"job_id": job_id, "status": JobStatus.QUEUED.value},
            {
                "$set": {
                    "status": JobStatus.CANCELLED.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"🚫 Job {job_id} cancelled")
            return True
        return False

