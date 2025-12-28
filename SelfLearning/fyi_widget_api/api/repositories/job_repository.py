"""Repository for job queue operations (API service view)."""

import logging
from datetime import datetime
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, IndexModel

from fyi_widget_api.api.models.job_models import JobStatus

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository for managing processing jobs (API service view)."""
    
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
        
        # Create new job document directly (API doesn't need ProcessingJob model)
        import uuid
        job_id = str(uuid.uuid4())
        job_dict = {
            "job_id": job_id,
            "blog_url": blog_url,
            "publisher_id": publisher_id,
            "config": config or {},
            "status": JobStatus.QUEUED.value,
            "failure_count": 0,
            "max_retries": 3,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.collection.insert_one(job_dict)
        logger.info(f"✅ Created job {job_id} for URL: {blog_url} (Publisher: {publisher_id})")
        
        return job_id, True
    
    async def get_job_by_id(self, job_id: str) -> Optional[dict]:
        """Get job by job_id (returns dict for API)."""
        job_dict = await self.collection.find_one({"job_id": job_id})
        return job_dict
    
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

