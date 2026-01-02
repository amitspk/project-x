"""Repository for blog_processing_queue collection - State management for blog processing."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class BlogProcessingStatus:
    """Status enum for blog processing queue."""
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRY = "retry"
    COMPLETED = "completed"
    FAILED = "failed"


class BlogProcessingQueueRepository:
    """
    Pure data access layer for blog_processing_queue collection.
    
    Responsibilities:
    - Generic CRUD operations
    - Atomic operations (race-condition safe)
    - No business logic or domain knowledge
    
    Business logic lives in BlogProcessingService.
    
    This collection maintains ONE entry per blog URL and tracks its current processing state.
    """

    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        collection_name: str = "blog_processing_queue"
    ):
        """Initialize repository with database connection."""
        self.database = database
        self.collection_name = collection_name
        self.collection = database[collection_name]
        logger.info(f"✅ BlogProcessingQueueRepository initialized (collection: {collection_name})")

    async def create_indexes(self):
        """Create necessary indexes for the collection."""
        try:
            # 1. Unique index on URL (prevent duplicates)
            await self.collection.create_index(
                "url",
                unique=True,
                name="url_unique"
            )
            
            # 2. Worker polling index (get oldest queued job)
            await self.collection.create_index(
                [("status", 1), ("created_at", 1)],
                name="worker_poll_idx"
            )
            
            # 3. Heartbeat monitoring index (find stale jobs)
            await self.collection.create_index(
                [("status", 1), ("heartbeat_at", 1)],
                name="heartbeat_monitor_idx"
            )
            
            # 4. Publisher queries
            await self.collection.create_index(
                [("publisher_id", 1), ("status", 1)],
                name="publisher_status_idx"
            )
            
            logger.info("✅ Created indexes for blog_processing_queue")
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
            raise

    async def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get blog processing entry by URL.
        
        Args:
            url: Blog URL (normalized)
            
        Returns:
            Blog entry document or None if not found
        """
        return await self.collection.find_one({"url": url})

    async def atomic_get_or_create(
        self,
        *,
        url: str,
        publisher_id: str,
        initial_status: str = BlogProcessingStatus.QUEUED,
    ) -> tuple[Dict[str, Any], bool]:
        """
        Atomically get existing entry or create new one.
        
        This prevents race conditions where two requests try to create the same entry.
        
        Args:
            url: Blog URL (normalized)
            publisher_id: Publisher ID
            initial_status: Initial status (default: queued)
            
        Returns:
            Tuple of (blog_entry_dict, is_new)
            - is_new=True if entry was just created
            - is_new=False if entry already existed
        """
        now = datetime.utcnow()
        
        # Try to create new entry
        new_entry = {
            "url": url,
            "publisher_id": publisher_id,
            "status": initial_status,
            "attempt_count": 0,
            "current_job_id": None,
            "worker_id": None,
            "last_error": None,
            "error_type": None,
            "heartbeat_at": None,
            "heartbeat_interval_seconds": 30,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
            "healed": False,
            "reprocessed_count": 0,
            "last_reprocessed_at": None,
            "tags": []
        }
        
        try:
            await self.collection.insert_one(new_entry)
            logger.info(f"✅ Created new blog_processing_queue entry for: {url}")
            return new_entry, True
            
        except DuplicateKeyError:
            # Entry already exists - fetch and return it
            existing = await self.get_by_url(url)
            if existing:
                logger.info(f"🔄 Blog already exists in queue: {url} (status: {existing.get('status')})")
                return existing, False
            else:
                # Shouldn't happen, but handle gracefully
                logger.error(f"❌ DuplicateKeyError but entry not found: {url}")
                raise

    async def atomic_update_status(
        self,
        *,
        url: str,
        from_status: Optional[str] = None,
        to_status: str,
        updates: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically update status with optional conditional check.
        
        This ensures only one process can transition a status at a time.
        
        Args:
            url: Blog URL
            from_status: Required current status (None = any status)
            to_status: New status to set
            updates: Additional fields to update
            
        Returns:
            Updated document or None if status check failed
        """
        query = {"url": url}
        if from_status:
            query["status"] = from_status
        
        update_doc = {
            "$set": {
                "status": to_status,
                "updated_at": datetime.utcnow(),
                **(updates or {})
            }
        }
        
        result = await self.collection.find_one_and_update(
            query,
            update_doc,
            return_document=ReturnDocument.AFTER
        )
        
        if result:
            logger.info(
                f"✅ Updated status: {url} "
                f"({from_status or 'any'} → {to_status})"
            )
        else:
            logger.warning(
                f"⚠️  Status update failed (condition not met): {url} "
                f"(expected: {from_status}, target: {to_status})"
            )
        
        return result

    async def atomic_requeue_failed(
        self,
        *,
        url: str,
        reset_attempts: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically requeue a failed blog for reprocessing.
        
        Only works if current status is "failed".
        
        Args:
            url: Blog URL
            reset_attempts: If True, reset attempt_count to 0 (fresh start)
            
        Returns:
            Updated document or None if not in failed state
        """
        updates = {
            "status": BlogProcessingStatus.QUEUED,
            "updated_at": datetime.utcnow(),
            "last_error": None,
            "error_type": None,
            "started_at": None,
            "completed_at": None,
            "worker_id": None,
            "current_job_id": None,
            "heartbeat_at": None
        }
        
        if reset_attempts:
            updates["attempt_count"] = 0
            updates["reprocessed_count"] = 1
            updates["last_reprocessed_at"] = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            {
                "url": url,
                "status": BlogProcessingStatus.FAILED
            },
            {"$set": updates},
            return_document=ReturnDocument.AFTER
        )
        
        if result:
            logger.info(f"✅ Requeued failed blog: {url}")
        else:
            logger.warning(f"⚠️  Cannot requeue (not in failed state): {url}")
        
        return result

    async def atomic_worker_pick_job(
        self,
        worker_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically pick a job from the queue (for worker).
        
        This prevents race conditions where multiple workers try to pick the same job.
        Picks the oldest queued or retry job (FIFO).
        
        Args:
            worker_id: Worker instance identifier
            
        Returns:
            Job document or None if no jobs available
        """
        now = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            {
                "status": {"$in": [BlogProcessingStatus.QUEUED, BlogProcessingStatus.RETRY]}
            },
            {
                "$set": {
                    "status": BlogProcessingStatus.PROCESSING,
                    "worker_id": worker_id,
                    "started_at": now,
                    "heartbeat_at": now,
                    "updated_at": now
                },
                "$inc": {
                    "attempt_count": 1
                }
            },
            sort=[("created_at", 1)],  # FIFO - oldest first
            return_document=ReturnDocument.AFTER
        )
        
        if result:
            logger.info(
                f"✅ Worker {worker_id} picked job: {result['url']} "
                f"(attempt {result['attempt_count']})"
            )
        
        return result

    async def atomic_batch_pick_sequential(
        self,
        worker_id: str,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Pick multiple blogs atomically using sequential atomic operations.
        
        This is the SAFEST approach for batch picking:
        - Each pick is atomic (no race conditions)
        - Guaranteed fair distribution across workers
        - No wasted database queries
        - Predictable behavior under contention
        
        Why sequential instead of batch query?
        - Batch queries have a gap between find() and update()
        - Multiple workers can see same blogs during that gap
        - Sequential atomics ensure each blog goes to ONE worker only
        
        Performance:
        - ~10ms per pick × 10 picks = 100ms total
        - Negligible compared to 60s processing time per blog
        
        Args:
            worker_id: Worker instance identifier
            batch_size: Number of blogs to pick (default: 10)
            
        Returns:
            List of blog entries (may be less than batch_size if queue is small)
        """
        blogs = []
        
        for _ in range(batch_size):
            # Each iteration is atomic - uses find_one_and_update
            blog = await self.atomic_worker_pick_job(worker_id)
            if blog:
                blogs.append(blog)
            else:
                # No more blogs available
                break
        
        if blogs:
            logger.info(
                f"📦 [{worker_id}] Picked batch of {len(blogs)} blogs "
                f"(requested: {batch_size})"
            )
        else:
            logger.debug(f"[{worker_id}] No blogs available in queue")
        
        return blogs

    async def update_heartbeat(
        self,
        worker_id: str,
        url: Optional[str] = None
    ) -> int:
        """
        Update heartbeat timestamp for processing job(s).
        
        If url is provided, updates only that specific job.
        If url is None, updates ALL jobs currently being processed by this worker.
        
        Args:
            worker_id: Worker instance identifier
            url: Optional specific blog URL (if None, updates all jobs for this worker)
            
        Returns:
            Number of documents updated
        """
        query = {
            "status": BlogProcessingStatus.PROCESSING,
            "worker_id": worker_id
        }
        
        if url:
            query["url"] = url
        
        result = await self.collection.update_many(
            query,
            {
                "$set": {
                    "heartbeat_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.debug(
                f"♥️  Updated heartbeat for worker {worker_id}: "
                f"{result.modified_count} job(s)"
            )
        
        return result.modified_count

    async def update(
        self,
        *,
        url: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Generic update method.
        
        Args:
            url: Blog URL
            updates: Fields to update
            
        Returns:
            True if document was modified
        """
        updates["updated_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"url": url},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def increment_field(
        self,
        *,
        url: str,
        field: str,
        amount: int = 1
    ) -> bool:
        """
        Generic increment method.
        
        Args:
            url: Blog URL
            field: Field name to increment
            amount: Amount to increment by
            
        Returns:
            True if document was modified
        """
        result = await self.collection.update_one(
            {"url": url},
            {
                "$inc": {field: amount},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0

    async def delete_by_url(self, url: str) -> bool:
        """
        Delete entry by URL (used for rollback on errors).
        
        Args:
            url: Blog URL
            
        Returns:
            True if document was deleted
        """
        result = await self.collection.delete_one({"url": url})
        success = result.deleted_count > 0
        if success:
            logger.info(f"✅ Deleted entry: {url}")
        return success

    async def get_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with counts per status
        """
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        stats = {
            BlogProcessingStatus.QUEUED: 0,
            BlogProcessingStatus.PROCESSING: 0,
            BlogProcessingStatus.RETRY: 0,
            BlogProcessingStatus.COMPLETED: 0,
            BlogProcessingStatus.FAILED: 0
        }
        
        async for doc in cursor:
            status = doc["_id"]
            count = doc["count"]
            stats[status] = count
        
        stats["total"] = sum(stats.values())
        return stats

