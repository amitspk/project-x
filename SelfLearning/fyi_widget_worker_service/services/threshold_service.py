"""Service for checking processing thresholds."""

import logging
from typing import Optional

from fyi_widget_worker_service.repositories import JobRepository
from fyi_widget_worker_service.models.publisher_models import PublisherConfig
from fyi_widget_worker_service.services.blog_content_repository import BlogContentRepository

logger = logging.getLogger(__name__)


class ThresholdService:
    """Service for checking if blog processing threshold is met."""
    
    def __init__(
        self,
        storage: BlogContentRepository,
        job_repo: JobRepository,
    ):
        """
        Initialize threshold service.
        
        Args:
            storage: BlogContentRepository instance
            job_repo: JobRepository instance
        """
        self.storage = storage
        self.job_repo = job_repo
    
    async def should_process_blog(
        self,
        blog_id: str,
        blog_doc: dict,
        config: PublisherConfig,
        job_id: str,
    ) -> tuple[bool, int]:
        """
        Check if blog should be processed based on threshold.
        
        Also increments triggered_no_of_times regardless of threshold.
        
        Args:
            blog_id: Blog document ID
            blog_doc: Blog document from database
            config: Publisher configuration
            job_id: Job ID for skipping if threshold not met
            
        Returns:
            Tuple of (should_process, new_triggered_count)
            - should_process: True if threshold is met
            - new_triggered_count: The new triggered count after increment
        """
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
                job_id=job_id,
                error_message=f"Threshold not met: triggered_count ({triggered_count + 1}) <= threshold ({threshold})"
            )
            
            logger.info(f"✅ Job {job_id} skipped due to threshold check")
        else:
            logger.info(
                f"✅ Threshold check passed: ({triggered_count} + 1) = {triggered_count + 1} > {threshold}. "
                f"Proceeding with processing..."
            )
        
        return should_process, new_triggered_count

