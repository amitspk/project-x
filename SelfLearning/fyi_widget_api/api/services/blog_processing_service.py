"""Service layer for blog processing business logic (v2 architecture)."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException

from fyi_widget_api.api.repositories.blog_processing_queue_repository import (
    BlogProcessingQueueRepository,
    BlogProcessingStatus as QueueStatus
)
from fyi_widget_api.api.repositories import (
    QuestionRepository,
    PublisherRepository,
)
from fyi_widget_api.api.repositories.blog_metadata_repository import BlogMetadataRepository
from fyi_widget_api.api.models.publisher_models import Publisher
from fyi_widget_api.api.repositories.publisher_repository import UsageLimitExceededError
from fyi_widget_api.api.services.publisher_service import PublisherService

logger = logging.getLogger(__name__)


class BlogProcessingService:
    """
    Business logic for blog processing operations.
    
    This service orchestrates:
    - Blog processing queue state management
    - Slot reservation/release
    - Job creation
    - State transitions
    
    Repositories handle data access, this service handles business rules.
    """

    def __init__(
        self,
        *,
        queue_repo: BlogProcessingQueueRepository,
        question_repo: QuestionRepository,
        publisher_repo: PublisherRepository,
        metadata_repo: BlogMetadataRepository,
    ):
        """
        Initialize service with injected repositories.
        
        Args:
            queue_repo: Blog processing queue repository
            question_repo: Question repository
            publisher_repo: Publisher repository
            metadata_repo: Blog metadata repository (for threshold tracking)
        """
        self.queue_repo = queue_repo
        self.question_repo = question_repo
        self.publisher_repo = publisher_repo
        self.metadata_repo = metadata_repo

    async def check_and_load_questions(
        self,
        *,
        normalized_url: str,
        publisher: Publisher,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Smart question loading with automatic job creation.
        
        Business Logic Flow:
        1. FAST PATH: Check if questions exist → return immediately
        2. Check blog_processing_queue for current state
        3. If new blog → Create entry + reserve slot + return "queued"
        4. If already queued/processing → Return current status
        5. If completed (but no questions) → Inconsistency, requeue
        6. If failed → Auto-requeue for retry (reset attempt count)
        
        Args:
            normalized_url: Normalized blog URL
            publisher: Publisher object
            request_id: Request ID for logging
            
        Returns:
            Dict with processing_status, questions, blog_info, job_id, message
        """
        # =====================================================================
        # STEP 1: FAST PATH - Check if questions already exist
        # =====================================================================
        questions = await self.question_repo.get_questions_by_url(normalized_url, limit=None)
        
        if questions:
            logger.info(f"[{request_id}] ⚡ Fast path: {len(questions)} questions found")
            
            # Don't heal - let reprocessing work naturally (per user decision)
            import random
            questions_copy = list(questions)
            random.shuffle(questions_copy)
            
            blog_info = await self.question_repo.get_blog_by_url(normalized_url)
            blog_id = questions_copy[0].blog_id
            
            questions_response = [
                {
                    "id": q.id,
                    "question": q.question,
                    "answer": q.answer,
                }
                for q in questions_copy
            ]
            
            return {
                "processing_status": "ready",
                "blog_url": normalized_url,
                "questions": questions_response,
                "blog_info": {
                    "id": blog_id,
                    "title": blog_info.get("title", "") if blog_info else "",
                    "url": normalized_url,
                    "author": blog_info.get("author", "") if blog_info else "",
                    "published_date": blog_info.get("published_date", "") if blog_info else "",
                    "question_count": len(questions_response),
                },
                "job_id": None,
                "message": "Questions ready - loaded from cache",
            }
        
        # =====================================================================
        # STEP 2: CHECK THRESHOLD - Increment counter and validate
        # =====================================================================
        logger.info(f"[{request_id}] 🔍 No questions found, checking threshold")
        
        # Atomically increment request count
        request_count = await self.metadata_repo.increment_and_get_count(
            url=normalized_url,
            publisher_id=publisher.id
        )
        
        # Get threshold from publisher config
        threshold = publisher.config.threshold_before_processing_blog
        
        # Check: request_count > threshold (e.g., if threshold=2, need 3 requests)
        should_process = request_count > threshold
        
        if not should_process:
            # Threshold not met - return early
            remaining = threshold - request_count + 1
            
            logger.info(
                f"[{request_id}] ⏭️  Threshold not met: "
                f"Request {request_count}/{threshold + 1}. Need {remaining} more."
            )
            
            return {
                "processing_status": "threshold_not_met",
                "blog_url": normalized_url,
                "questions": None,
                "blog_info": None,
                "job_id": None,
                "message": (
                    f"This blog will be processed after {remaining} more request(s). "
                    f"Progress: {request_count}/{threshold + 1}"
                ),
                "threshold_info": {
                    "current_requests": request_count,
                    "required_requests": threshold + 1,
                    "remaining_requests": remaining,
                    "threshold": threshold,
                },
            }
        
        logger.info(
            f"[{request_id}] ✅ Threshold met ({request_count}/{threshold + 1}), "
            f"proceeding with processing"
        )
        
        # =====================================================================
        # STEP 3: No questions - check blog_processing_queue state
        # =====================================================================
        logger.info(f"[{request_id}] 🔄 Checking processing queue")
        
        blog_entry, is_new = await self.queue_repo.atomic_get_or_create(
            url=normalized_url,
            publisher_id=publisher.id,
            initial_status=QueueStatus.QUEUED
        )
        
        # =====================================================================
        # STEP 4: NEW ENTRY - Reserve slot and return "queued"
        # =====================================================================
        if is_new:
            logger.info(f"[{request_id}] 🆕 New blog entry created")
            
            # Validate whitelist before reserving slot
            PublisherService.ensure_url_whitelisted(normalized_url, publisher)
            
            # Reserve slot in PostgreSQL (atomic operation)
            try:
                await self.publisher_repo.reserve_blog_slot(publisher.id)
                logger.info(f"[{request_id}] ✅ Slot reserved for publisher {publisher.id}")
            except UsageLimitExceededError as exc:
                # Rollback: Delete MongoDB entry
                logger.error(f"[{request_id}] ❌ Slot reservation failed: {exc}")
                await self.queue_repo.delete_by_url(normalized_url)
                raise HTTPException(status_code=403, detail=str(exc))
            except Exception as e:
                # Rollback on any error
                logger.error(f"[{request_id}] ❌ Unexpected error during slot reservation: {e}")
                await self.queue_repo.delete_by_url(normalized_url)
                raise
            
            return {
                "processing_status": "not_started",
                "blog_url": normalized_url,
                "questions": None,
                "blog_info": None,
                "job_id": blog_entry.get("current_job_id"),
                "message": "Processing started - check back in 30-60 seconds",
            }
        
        # =====================================================================
        # STEP 5: EXISTING ENTRY - Check current status
        # =====================================================================
        status = blog_entry["status"]
        logger.info(f"[{request_id}] 📊 Existing entry found: status={status}")
        
        # ---------------------------------------------------------------------
        # 4a. Already queued or processing
        # ---------------------------------------------------------------------
        if status in [QueueStatus.QUEUED, QueueStatus.PROCESSING, QueueStatus.RETRY]:
            status_messages = {
                QueueStatus.QUEUED: "Blog processing is queued",
                QueueStatus.PROCESSING: "Blog is currently being processed",
                QueueStatus.RETRY: "Blog processing is queued for retry"
            }
            
            return {
                "processing_status": status,
                "blog_url": normalized_url,
                "questions": None,
                "blog_info": None,
                "job_id": blog_entry.get("current_job_id"),
                "message": status_messages.get(status, f"Blog is {status}"),
            }
        
        # ---------------------------------------------------------------------
        # 4b. Completed but no questions (inconsistency)
        # ---------------------------------------------------------------------
        if status == QueueStatus.COMPLETED:
            logger.warning(
                f"[{request_id}] ⚠️  Inconsistency: status=completed but no questions found. "
                f"Requeuing for reprocessing."
            )
            
            # Requeue atomically
            result = await self.queue_repo.atomic_update_status(
                url=normalized_url,
                from_status=QueueStatus.COMPLETED,
                to_status=QueueStatus.QUEUED,
                updates={
                    "attempt_count": 0,  # Reset attempts
                    "last_error": None,
                    "error_type": None,
                    "started_at": None,
                    "completed_at": None,
                    "worker_id": None,
                    "current_job_id": None,
                    "heartbeat_at": None,
                }
            )
            
            if result:
                return {
                    "processing_status": "queued",
                    "blog_url": normalized_url,
                    "questions": None,
                    "blog_info": None,
                    "job_id": None,
                    "message": "Reprocessing initiated due to data inconsistency",
                }
            else:
                # Status changed by another process
                logger.warning(f"[{request_id}] ⚠️  Status changed during requeue attempt")
                return {
                    "processing_status": "processing",
                    "blog_url": normalized_url,
                    "questions": None,
                    "blog_info": None,
                    "job_id": blog_entry.get("current_job_id"),
                    "message": "Blog is being processed",
                }
        
        # ---------------------------------------------------------------------
        # 4c. Failed - Auto-requeue for retry
        # ---------------------------------------------------------------------
        if status == QueueStatus.FAILED:
            attempt_count = blog_entry.get("attempt_count", 0)
            last_error = blog_entry.get("last_error", "")
            
            logger.info(
                f"[{request_id}] 🔄 Blog failed previously (attempts: {attempt_count}). "
                f"Auto-requeuing with reset attempt count."
            )
            
            # Use atomic requeue method (resets attempt count per user decision)
            result = await self.queue_repo.atomic_requeue_failed(
                url=normalized_url,
                reset_attempts=True  # Fresh start
            )
            
            if result:
                # Reserve slot for reprocessing (slot was released on failure)
                try:
                    await self.publisher_repo.reserve_blog_slot(publisher.id)
                    logger.info(f"[{request_id}] ✅ Slot reserved for reprocessing")
                except UsageLimitExceededError as exc:
                    # Revert back to failed
                    logger.error(f"[{request_id}] ❌ Cannot reprocess: {exc}")
                    await self.queue_repo.atomic_update_status(
                        url=normalized_url,
                        from_status=QueueStatus.QUEUED,
                        to_status=QueueStatus.FAILED,
                        updates={
                            "last_error": str(exc),
                            "error_type": "usage_limit_exceeded"
                        }
                    )
                    raise HTTPException(status_code=403, detail=str(exc))
                
                return {
                    "processing_status": "queued",
                    "blog_url": normalized_url,
                    "questions": None,
                    "blog_info": None,
                    "job_id": None,
                    "message": f"Reprocessing initiated (previous error: {last_error})",
                }
            else:
                # Couldn't requeue (status changed)
                logger.warning(f"[{request_id}] ⚠️  Could not requeue failed blog")
                return {
                    "processing_status": "failed",
                    "blog_url": normalized_url,
                    "questions": None,
                    "blog_info": None,
                    "job_id": blog_entry.get("current_job_id"),
                    "message": f"Processing failed: {last_error}",
                }
        
        # ---------------------------------------------------------------------
        # Unknown status (shouldn't happen)
        # ---------------------------------------------------------------------
        logger.error(f"[{request_id}] ❌ Unknown status: {status}")
        return {
            "processing_status": "unknown",
            "blog_url": normalized_url,
            "questions": None,
            "blog_info": None,
            "job_id": blog_entry.get("current_job_id"),
            "message": f"Unknown processing status: {status}",
        }

    async def reprocess_blog(
        self,
        *,
        blog_url: str,
        publisher: Publisher,
        reason: Optional[str] = None,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Manually trigger reprocessing of a blog.
        
        Business Logic:
        - Only reprocess if status is "completed" or "failed"
        - Cannot reprocess if currently "queued", "processing", or "retry"
        - Resets attempt count to 0 (fresh start)
        - Reserves new slot if coming from "failed" state
        
        Args:
            blog_url: Blog URL to reprocess
            publisher: Publisher object
            reason: Optional reason for reprocessing
            request_id: Request ID for logging
            
        Returns:
            Dict with status and message
            
        Raises:
            HTTPException: If blog not found or in invalid state
        """
        logger.info(f"[{request_id}] 🔄 Admin reprocess request for: {blog_url}")
        
        # Get current entry
        blog_entry = await self.queue_repo.get_by_url(blog_url)
        
        if not blog_entry:
            logger.error(f"[{request_id}] ❌ Blog not found in processing queue")
            raise HTTPException(
                status_code=404,
                detail=f"Blog not found in processing queue: {blog_url}"
            )
        
        current_status = blog_entry["status"]
        
        # Check if reprocessing is allowed
        if current_status in [QueueStatus.QUEUED, QueueStatus.PROCESSING, QueueStatus.RETRY]:
            logger.error(
                f"[{request_id}] ❌ Cannot reprocess: blog is currently {current_status}"
            )
            raise HTTPException(
                status_code=409,
                detail=f"Cannot reprocess: blog is currently {current_status}. "
                       f"Wait for current processing to complete."
            )
        
        # Reprocess from completed or failed state
        logger.info(
            f"[{request_id}] ✅ Reprocessing allowed. Current status: {current_status}"
        )
        
        # Atomic update with status check
        updates = {
            "attempt_count": 0,  # Reset attempts
            "last_error": None,
            "error_type": None,
            "started_at": None,
            "completed_at": None,
            "worker_id": None,
            "current_job_id": None,
            "heartbeat_at": None,
            "last_reprocessed_at": datetime.utcnow(),
            "was_previously_completed": current_status == QueueStatus.COMPLETED,  # Track if reprocessing completed blog
        }
        
        # Increment reprocess count
        await self.queue_repo.increment_field(
            url=blog_url,
            field="reprocessed_count",
            amount=1
        )
        
        # Update status to queued
        result = await self.queue_repo.atomic_update_status(
            url=blog_url,
            from_status=current_status,
            to_status=QueueStatus.QUEUED,
            updates=updates
        )
        
        if not result:
            logger.error(f"[{request_id}] ❌ Status changed during reprocess")
            raise HTTPException(
                status_code=409,
                detail="Blog status changed during reprocess. Please retry."
            )
        
        # If coming from failed state, need to reserve slot again
        if current_status == QueueStatus.FAILED:
            try:
                await self.publisher_repo.reserve_blog_slot(publisher.id)
                logger.info(f"[{request_id}] ✅ Slot reserved for reprocessing")
            except UsageLimitExceededError as exc:
                # Revert back to failed
                logger.error(f"[{request_id}] ❌ Cannot reprocess: {exc}")
                await self.queue_repo.atomic_update_status(
                    url=blog_url,
                    from_status=QueueStatus.QUEUED,
                    to_status=QueueStatus.FAILED,
                    updates={
                        "last_error": str(exc),
                        "error_type": "usage_limit_exceeded"
                    }
                )
                raise HTTPException(status_code=403, detail=str(exc))
        
        logger.info(
            f"[{request_id}] ✅ Blog requeued for reprocessing. "
            f"Reason: {reason or 'Manual reprocess'}"
        )
        
        return {
            "status": "success",
            "blog_url": blog_url,
            "previous_status": current_status,
            "new_status": "queued",
            "message": f"Blog requeued for reprocessing. Reason: {reason or 'Manual reprocess'}",
            "reprocess_count": result.get("reprocessed_count", 1)
        }

