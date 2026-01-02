"""Repository for blog_processing_audit collection - Append-only audit trail."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class AuditStatus:
    """Status enum for audit entries."""
    COMPLETED = "completed"
    FAILED = "failed"


class BlogProcessingAuditRepository:
    """
    Pure data access layer for blog_processing_audit collection.
    
    Responsibilities:
    - Append-only audit trail writes
    - Query audit history
    - No business logic or domain knowledge
    
    This collection stores ALL processing attempts (successful and failed).
    Multiple entries per blog URL are expected.
    """

    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        collection_name: str = "blog_processing_audit"
    ):
        """Initialize repository with database connection."""
        self.database = database
        self.collection_name = collection_name
        self.collection = database[collection_name]
        logger.info(f"✅ BlogProcessingAuditRepository initialized (collection: {collection_name})")

    async def create_indexes(self):
        """Create necessary indexes for the collection."""
        try:
            # 1. Index on URL for blog history lookup
            await self.collection.create_index(
                [("url", 1), ("created_at", -1)],
                name="url_history_idx"
            )
            
            # 2. Publisher analytics index
            await self.collection.create_index(
                [("publisher_id", 1), ("created_at", -1)],
                name="publisher_analytics_idx"
            )
            
            # 3. Status metrics index
            await self.collection.create_index(
                [("status", 1), ("created_at", -1)],
                name="status_metrics_idx"
            )
            
            # 4. Time-based queries
            await self.collection.create_index(
                [("created_at", -1)],
                name="created_at_idx"
            )
            
            # 5. Job ID lookup
            await self.collection.create_index(
                "job_id",
                name="job_id_idx"
            )
            
            logger.info("✅ Created indexes for blog_processing_audit")
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
            raise

    async def insert_audit_entry(
        self,
        *,
        url: str,
        publisher_id: str,
        job_id: str,
        worker_id: str,
        status: str,
        attempt_number: int,
        processing_time_seconds: float,
        started_at: datetime,
        completed_at: datetime,
        question_count: Optional[int] = None,
        summary_length: Optional[int] = None,
        embedding_count: Optional[int] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        error_stack_trace: Optional[str] = None,
        blog_title: Optional[str] = None,
        blog_content_length: Optional[int] = None,
        blog_author: Optional[str] = None,
        llm_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        publisher_config: Optional[Dict[str, Any]] = None,
        is_reprocess: bool = False,
        reprocess_reason: Optional[str] = None,
    ) -> str:
        """
        Insert a new audit entry (append-only).
        
        Args:
            url: Blog URL
            publisher_id: Publisher ID
            job_id: Job ID from processing_jobs
            worker_id: Worker instance identifier
            status: Final status (completed or failed)
            attempt_number: Which attempt this was (1-3)
            processing_time_seconds: How long processing took
            started_at: When processing started
            completed_at: When processing completed/failed
            question_count: Number of questions generated (if successful)
            summary_length: Summary character count (if successful)
            embedding_count: Number of embeddings created (if successful)
            error_message: Error message (if failed)
            error_type: Error category (if failed)
            error_stack_trace: Full stack trace (if failed)
            blog_title: Blog title at processing time
            blog_content_length: Original content length
            blog_author: Blog author
            llm_model: Which LLM model was used
            embedding_model: Which embedding model was used
            publisher_config: Publisher config snapshot
            is_reprocess: True if this was a manual reprocess
            reprocess_reason: Why it was reprocessed
            
        Returns:
            Inserted document ID as string
        """
        now = datetime.utcnow()
        
        entry = {
            "url": url,
            "publisher_id": publisher_id,
            "job_id": job_id,
            "worker_id": worker_id,
            "status": status,
            "attempt_number": attempt_number,
            "processing_time_seconds": processing_time_seconds,
            "started_at": started_at,
            "completed_at": completed_at,
            "created_at": now,
        }
        
        # Add optional fields only if provided (keep document lean)
        if question_count is not None:
            entry["question_count"] = question_count
        if summary_length is not None:
            entry["summary_length"] = summary_length
        if embedding_count is not None:
            entry["embedding_count"] = embedding_count
        if error_message is not None:
            entry["error_message"] = error_message
        if error_type is not None:
            entry["error_type"] = error_type
        if error_stack_trace is not None:
            entry["error_stack_trace"] = error_stack_trace
        if blog_title is not None:
            entry["blog_title"] = blog_title
        if blog_content_length is not None:
            entry["blog_content_length"] = blog_content_length
        if blog_author is not None:
            entry["blog_author"] = blog_author
        if llm_model is not None:
            entry["llm_model"] = llm_model
        if embedding_model is not None:
            entry["embedding_model"] = embedding_model
        if publisher_config is not None:
            entry["publisher_config"] = publisher_config
        if is_reprocess:
            entry["is_reprocess"] = is_reprocess
        if reprocess_reason is not None:
            entry["reprocess_reason"] = reprocess_reason
        
        result = await self.collection.insert_one(entry)
        
        logger.info(
            f"✅ Audit entry created: {url} "
            f"(status={status}, attempt={attempt_number}, time={processing_time_seconds:.2f}s)"
        )
        
        return str(result.inserted_id)

    async def get_by_url(
        self,
        url: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit history for a specific blog URL.
        
        Args:
            url: Blog URL
            limit: Maximum number of entries to return (None = all)
            
        Returns:
            List of audit entries, newest first
        """
        cursor = self.collection.find(
            {"url": url}
        ).sort("created_at", -1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        entries = []
        async for doc in cursor:
            entries.append(doc)
        
        return entries

    async def get_by_job_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get audit entry by job ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Audit entry or None if not found
        """
        return await self.collection.find_one({"job_id": job_id})

    async def get_by_publisher(
        self,
        publisher_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit history for a publisher.
        
        Args:
            publisher_id: Publisher ID
            status: Filter by status (None = all)
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries, newest first
        """
        query = {"publisher_id": publisher_id}
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query).sort("created_at", -1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        entries = []
        async for doc in cursor:
            entries.append(doc)
        
        return entries

    async def get_recent(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit entries.
        
        Args:
            status: Filter by status (None = all)
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries, newest first
        """
        query = {}
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        
        entries = []
        async for doc in cursor:
            entries.append(doc)
        
        return entries

    async def get_stats(
        self,
        publisher_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit statistics.
        
        Args:
            publisher_id: Filter by publisher (None = all)
            start_date: Start date filter (None = all time)
            end_date: End date filter (None = all time)
            
        Returns:
            Dictionary with statistics
        """
        match_stage = {}
        if publisher_id:
            match_stage["publisher_id"] = publisher_id
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            match_stage["created_at"] = date_filter
        
        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        pipeline.append({
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "avg_processing_time": {"$avg": "$processing_time_seconds"},
                "total_questions": {"$sum": "$question_count"}
            }
        })
        
        cursor = self.collection.aggregate(pipeline)
        
        stats = {
            "completed": 0,
            "failed": 0,
            "total": 0,
            "avg_processing_time_completed": 0.0,
            "avg_processing_time_failed": 0.0,
            "total_questions_generated": 0
        }
        
        async for doc in cursor:
            status = doc["_id"]
            count = doc["count"]
            avg_time = doc.get("avg_processing_time", 0) or 0
            total_questions = doc.get("total_questions", 0) or 0
            
            if status == AuditStatus.COMPLETED:
                stats["completed"] = count
                stats["avg_processing_time_completed"] = avg_time
                stats["total_questions_generated"] = total_questions
            elif status == AuditStatus.FAILED:
                stats["failed"] = count
                stats["avg_processing_time_failed"] = avg_time
        
        stats["total"] = stats["completed"] + stats["failed"]
        
        return stats

    async def get_failure_analysis(
        self,
        publisher_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze failure patterns.
        
        Args:
            publisher_id: Filter by publisher (None = all)
            limit: Maximum number of error types to return
            
        Returns:
            Dictionary with failure analysis
        """
        match_stage = {"status": AuditStatus.FAILED}
        if publisher_id:
            match_stage["publisher_id"] = publisher_id
        
        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$error_type",
                    "count": {"$sum": 1},
                    "example_error": {"$first": "$error_message"}
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        cursor = self.collection.aggregate(pipeline)
        
        error_types = []
        total_failures = 0
        
        async for doc in cursor:
            error_types.append({
                "error_type": doc["_id"],
                "count": doc["count"],
                "example_error": doc.get("example_error")
            })
            total_failures += doc["count"]
        
        return {
            "total_failures": total_failures,
            "error_types": error_types
        }

