"""Service layer for question-related operations."""

import logging
from typing import Any, Dict
from bson import ObjectId
from fastapi import HTTPException

from fyi_widget_api.api.repositories import PublisherRepository, QuestionRepository
from fyi_widget_api.api.models.publisher_models import Publisher

logger = logging.getLogger(__name__)


class QuestionService:
    """Question service with constructor-injected dependencies."""

    def __init__(
        self,
        question_repo: QuestionRepository,
        publisher_repo: PublisherRepository,
    ):
        self.question_repo = question_repo
        self.publisher_repo = publisher_repo

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
        """
        Delete a blog and all related data across all collections.
        
        Deletes from 5 collections in a single atomic transaction:
        1. blog_meta_data (threshold tracking)
        2. blog_processing_queue (V2 queue)
        3. raw_blog_content (original content)
        4. blog_summaries (summary + embedding)
        5. processed_questions (all Q&A pairs)
        """
        try:
            ObjectId(blog_id)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid blog_id format: {blog_id}",
            )

        result = await self.question_repo.delete_blog(blog_id)
        deleted = result.get("deleted", {})
        
        return {
            "blog_id": blog_id,
            "blog_url": result.get("blog_url"),
            "transaction_status": result.get("transaction"),
            "deleted_counts": {
                "blog_meta_data": deleted.get("blog_meta_data", 0),
                "blog_processing_queue": deleted.get("blog_processing_queue", 0),
                "raw_blog_content": deleted.get("raw_blog_content", 0),
                "blog_summaries": deleted.get("blog_summaries", 0),
                "processed_questions": deleted.get("processed_questions", 0)
            },
            "total_deleted": sum(deleted.values())
        }
