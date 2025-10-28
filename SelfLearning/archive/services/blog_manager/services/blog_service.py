"""
Business logic service for blog operations.

Implements the business logic for blog-related operations, coordinating between
repositories and providing high-level functionality for the API layer.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from urllib.parse import urlparse

from ..data.repositories import BlogRepository, QuestionRepository, SummaryRepository
from ..models.response_models import (
    BlogQuestionsResponse,
    QuestionModel,
    BlogInfoModel,
    SummaryModel
)
from ..models.mongodb_models import BlogDocument, QuestionDocument, SummaryDocument
from ..core.exceptions import (
    BlogNotFoundException,
    NoQuestionsFoundException,
    InvalidUrlException,
    ValidationException
)

logger = logging.getLogger(__name__)


class BlogService:
    """Service class for blog-related business logic."""
    
    def __init__(self):
        self.blog_repo = BlogRepository()
        self.question_repo = QuestionRepository()
        self.summary_repo = SummaryRepository()
    
    async def get_blog_questions_by_url(
        self,
        url: str,
        include_summary: bool = False,
        include_metadata: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> BlogQuestionsResponse:
        """
        Get blog questions by URL.
        
        Args:
            url: Blog URL to lookup
            include_summary: Whether to include blog summary
            include_metadata: Whether to include question metadata
            limit: Maximum number of questions to return
            offset: Number of questions to skip
            
        Returns:
            BlogQuestionsResponse with questions and metadata
            
        Raises:
            BlogNotFoundException: If blog is not found
            NoQuestionsFoundException: If no questions exist for the blog
            InvalidUrlException: If URL format is invalid
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate URL
            self._validate_url(url)
            
            # Find blog by URL
            blog = await self.blog_repo.find_by_url(url)
            if not blog:
                raise BlogNotFoundException(url, "URL")
            
            # Get questions
            questions = await self.question_repo.find_by_blog_id(
                blog.blog_id,
                limit=limit,
                skip=offset
            )
            
            if not questions:
                raise NoQuestionsFoundException(blog.blog_id)
            
            # Get total question count
            total_questions = await self.question_repo.count_by_blog_id(blog.blog_id)
            
            # Get summary if requested
            summary = None
            if include_summary:
                summary_doc = await self.summary_repo.find_by_blog_id(blog.blog_id)
                if summary_doc:
                    summary = self._convert_summary_to_model(summary_doc)
            
            # Convert to response models
            blog_info = self._convert_blog_to_info_model(blog)
            question_models = [
                self._convert_question_to_model(q, include_metadata)
                for q in questions
            ]
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Calculate metadata
            avg_confidence = sum(q.question_quality_score for q in questions) / len(questions)
            has_more = (offset + len(questions)) < total_questions
            
            return BlogQuestionsResponse(
                success=True,
                blog_info=blog_info,
                questions=question_models,
                summary=summary,
                total_questions=total_questions,
                returned_questions=len(question_models),
                has_more=has_more,
                generated_at=questions[0].generated_at if questions else None,
                ai_model=questions[0].ai_model if questions else None,
                average_confidence=avg_confidence,
                processing_time_ms=processing_time
            )
            
        except (BlogNotFoundException, NoQuestionsFoundException, InvalidUrlException):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting blog questions by URL {url}: {e}")
            raise Exception(f"Failed to get blog questions: {e}")
    
    async def get_blog_questions_by_id(
        self,
        blog_id: str,
        include_summary: bool = False,
        include_metadata: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> BlogQuestionsResponse:
        """Get blog questions by blog ID."""
        start_time = datetime.utcnow()
        
        try:
            # Find blog by ID
            blog = await self.blog_repo.find_by_blog_id(blog_id)
            if not blog:
                raise BlogNotFoundException(blog_id, "blog_id")
            
            # Get questions
            questions = await self.question_repo.find_by_blog_id(
                blog_id,
                limit=limit,
                skip=offset
            )
            
            if not questions:
                raise NoQuestionsFoundException(blog_id)
            
            # Get total question count
            total_questions = await self.question_repo.count_by_blog_id(blog_id)
            
            # Get summary if requested
            summary = None
            if include_summary:
                summary_doc = await self.summary_repo.find_by_blog_id(blog_id)
                if summary_doc:
                    summary = self._convert_summary_to_model(summary_doc)
            
            # Convert to response models
            blog_info = self._convert_blog_to_info_model(blog)
            question_models = [
                self._convert_question_to_model(q, include_metadata)
                for q in questions
            ]
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Calculate metadata
            avg_confidence = sum(q.question_quality_score for q in questions) / len(questions)
            has_more = (offset + len(questions)) < total_questions
            
            return BlogQuestionsResponse(
                success=True,
                blog_info=blog_info,
                questions=question_models,
                summary=summary,
                total_questions=total_questions,
                returned_questions=len(question_models),
                has_more=has_more,
                generated_at=questions[0].generated_at if questions else None,
                ai_model=questions[0].ai_model if questions else None,
                average_confidence=avg_confidence,
                processing_time_ms=processing_time
            )
            
        except (BlogNotFoundException, NoQuestionsFoundException):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting blog questions by ID {blog_id}: {e}")
            raise Exception(f"Failed to get blog questions: {e}")
    
    async def search_blogs(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[BlogInfoModel]:
        """Search blogs by text query."""
        try:
            blogs = await self.blog_repo.search_blogs(query, limit, offset)
            return [self._convert_blog_to_info_model(blog) for blog in blogs]
        except Exception as e:
            logger.error(f"Error searching blogs with query {query}: {e}")
            raise Exception(f"Failed to search blogs: {e}")
    
    async def get_recent_blogs(self, limit: int = 10) -> List[BlogInfoModel]:
        """Get recently added blogs."""
        try:
            blogs = await self.blog_repo.get_recent_blogs(limit)
            return [self._convert_blog_to_info_model(blog) for blog in blogs]
        except Exception as e:
            logger.error(f"Error getting recent blogs: {e}")
            raise Exception(f"Failed to get recent blogs: {e}")
    
    async def get_blog_statistics(self) -> Dict[str, Any]:
        """Get overall blog statistics."""
        try:
            # This would require additional repository methods
            # For now, return basic stats
            recent_blogs = await self.blog_repo.get_recent_blogs(1)
            
            return {
                "total_blogs": len(recent_blogs),  # Simplified for demo
                "recent_blogs_available": len(recent_blogs) > 0,
                "last_updated": recent_blogs[0].created_at if recent_blogs else None
            }
        except Exception as e:
            logger.error(f"Error getting blog statistics: {e}")
            raise Exception(f"Failed to get blog statistics: {e}")
    
    def _validate_url(self, url: str) -> None:
        """Validate URL format."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise InvalidUrlException(url)
        except Exception:
            raise InvalidUrlException(url)
    
    def _convert_blog_to_info_model(self, blog: BlogDocument) -> BlogInfoModel:
        """Convert BlogDocument to BlogInfoModel."""
        return BlogInfoModel(
            blog_id=blog.blog_id,
            title=blog.title,
            url=blog.url,
            author=blog.author,
            published_date=blog.published_date,
            word_count=blog.word_count,
            source_domain=blog.source_domain
        )
    
    def _convert_question_to_model(
        self,
        question: QuestionDocument,
        include_metadata: bool = True
    ) -> QuestionModel:
        """Convert QuestionDocument to QuestionModel."""
        model_data = {
            "id": str(question.id),
            "question": question.question,
            "answer": question.answer,
            "question_type": question.question_type,
            "question_order": question.question_order,
            "confidence_score": question.question_quality_score
        }
        
        if include_metadata:
            model_data.update({
                "difficulty_level": question.difficulty_level,
                "topic_area": question.topic_area,
                "bloom_taxonomy_level": question.bloom_taxonomy_level,
                "learning_objective": question.learning_objective,
                "estimated_answer_time": int(question.processing_time_seconds) if question.processing_time_seconds else None
            })
        
        return QuestionModel(**model_data)
    
    def _convert_summary_to_model(self, summary: SummaryDocument) -> SummaryModel:
        """Convert SummaryDocument to SummaryModel."""
        return SummaryModel(
            summary_text=summary.summary_text,
            key_points=summary.key_points,
            main_topics=summary.main_topics,
            confidence_score=summary.confidence_score,
            word_count=len(summary.summary_text.split()) if summary.summary_text else 0
        )
