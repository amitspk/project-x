"""Service layer for question-related operations."""

import logging
import random
from typing import Any, Dict, Optional
from bson import ObjectId
from fastapi import HTTPException

from fyi_widget_api.api.repositories import JobRepository, PublisherRepository, QuestionRepository
from fyi_widget_api.api.models.publisher_models import Publisher
from fyi_widget_api.api.repositories.publisher_repository import UsageLimitExceededError
from fyi_widget_api.api.services.publisher_service import PublisherService

logger = logging.getLogger(__name__)


class QuestionService:
    """Question service with constructor-injected dependencies."""

    def __init__(
        self,
        question_repo: QuestionRepository,
        job_repo: JobRepository,
        publisher_repo: PublisherRepository,
    ):
        self.question_repo = question_repo
        self.job_repo = job_repo
        self.publisher_repo = publisher_repo

    async def check_and_load_questions(
        self,
        *,
        normalized_url: str,
        publisher: Publisher,
        request_id: str,
    ) -> Dict[str, Any]:
        """Fast-path load questions or enqueue processing if missing."""
        # STEP 1: Check if questions already exist
        questions = await self.question_repo.get_questions_by_url(normalized_url, limit=None)

        if questions:
            logger.info(f"[{request_id}] ⚡ Fast path: {len(questions)} questions found, returning immediately")

            questions_copy = list(questions)
            random.shuffle(questions_copy)

            blog_info = await self.question_repo.get_blog_by_url(normalized_url)
        blog_id = questions_copy[0].blog_id

        questions_response = []
        for q in questions_copy:
            q_dict = q.model_dump() if hasattr(q, "model_dump") else q.dict()
            questions_response.append(
                {
                    "id": q_dict.get("id"),
                    "question": q_dict.get("question"),
                    "answer": q_dict.get("answer"),
                }
            )

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

        # STEP 2: No questions found - check for existing job
        logger.info(f"[{request_id}] 🔄 No questions found, checking for existing job")

        existing_job = await self.job_repo.collection.find_one(
            {"blog_url": normalized_url, "status": {"$in": ["pending", "processing"]}},
            sort=[("created_at", -1)],
        )

        if existing_job:
            job_status = existing_job.get("status")
            job_id = str(existing_job.get("_id"))

            processing_status = "processing"
            message = "Blog is currently being processed" if job_status == "processing" else "Blog processing is queued"

            return {
                "processing_status": processing_status,
                "blog_url": normalized_url,
                "questions": None,
                "blog_info": None,
                "job_id": job_id,
                "message": message,
            }

        # STEP 3: No active job - create new processing job
        from fyi_widget_api.api.models.job_models import JobStatus

        logger.info(f"[{request_id}] 🚀 Creating new processing job")

        publisher_config = publisher.config.dict() if publisher.config else {}

        PublisherService.ensure_url_whitelisted(normalized_url, publisher)

        slot_reserved = False
        try:
            if self.publisher_repo:
                await self.publisher_repo.reserve_blog_slot(publisher.id)
                slot_reserved = True

            job_id, is_new_job = await self.job_repo.create_job(
                blog_url=normalized_url, publisher_id=publisher.id, config=publisher_config
            )

            if slot_reserved and not is_new_job and self.publisher_repo:
                await self.publisher_repo.release_blog_slot(
                    publisher.id,
                    processed=False,
                )
                slot_reserved = False

        except UsageLimitExceededError as exc:
            logger.warning(f"[{request_id}] ❌ Blog limit reached for publisher {publisher.id}: {exc}")
            raise HTTPException(
                status_code=403,
                detail=str(exc),
            )
        except Exception:
            if slot_reserved and self.publisher_repo:
                try:
                    await self.publisher_repo.release_blog_slot(
                        publisher.id,
                        processed=False,
                    )
                except Exception as release_error:  # pragma: no cover - logging only
                    logger.warning(f"[{request_id}] ⚠️ Failed to release reserved blog slot: {release_error}")
            raise

        return {
            "processing_status": "not_started",
            "blog_url": normalized_url,
            "questions": None,
            "blog_info": None,
            "job_id": job_id,
            "message": "Processing started - check back in 30-60 seconds",
        }

    async def get_questions_by_url(
        self,
        *,
        normalized_url: str,
        publisher: Publisher,
        request_id: str,
        original_blog_url: str,
    ) -> Dict[str, Any]:
        """Fetch all questions for a blog."""
        questions = await self.question_repo.get_questions_by_url(normalized_url, limit=None)

        if not questions:
            raise HTTPException(
                status_code=404,
                detail=f"No questions found for URL: {original_blog_url}",
            )

        questions_copy = list(questions)
        random.shuffle(questions_copy)

        blog_info = await self.question_repo.get_blog_by_url(normalized_url)
        blog_id = questions_copy[0].blog_id

        questions_response = []
        for q in questions_copy:
            q_dict = q.model_dump() if hasattr(q, "model_dump") else q.dict()
            questions_response.append(
                {
                    "id": q_dict.get("id"),
                    "question": q_dict.get("question"),
                    "answer": q_dict.get("answer"),
                }
            )

        return {
            "questions": questions_response,
            "blog_info": {
                "id": blog_id,
                "title": blog_info.get("title", "") if blog_info else "",
                "url": original_blog_url,
                "author": blog_info.get("author", "") if blog_info else "",
                "published_date": blog_info.get("published_date", "") if blog_info else "",
                "question_count": len(questions),
            },
        }

    async def get_question_by_id(
        self,
        *,
        question_id: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """Return a single question by id."""
        question = await self.question_repo.get_question_by_id(question_id)

        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question not found: {question_id}",
            )

        question["id"] = str(question["_id"])
        question.pop("_id", None)
        question.pop("embedding", None)
        question.pop("click_count", None)
        question.pop("last_clicked_at", None)
        question.pop("icon", None)

        if "created_at" in question and question["created_at"] and hasattr(question["created_at"], "isoformat"):
            question["created_at"] = question["created_at"].isoformat()

        return question

    async def delete_blog_by_id(
        self,
        *,
        blog_id: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """Delete a blog and all related data."""
        try:
            ObjectId(blog_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid blog_id format: {blog_id}",
            )

        result = await self.question_repo.delete_blog(blog_id)
        # Convert to expected format
        deleted = result.get("deleted", {})
        return {
            "blog_deleted": deleted.get("blog", 0) > 0,
            "questions_deleted": deleted.get("questions", 0),
            "summary_deleted": deleted.get("summary", 0) > 0,
            "blog_id": blog_id,
        }
