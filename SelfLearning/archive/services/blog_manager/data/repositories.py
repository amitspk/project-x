"""
Repository classes for data access in the blog manager microservice.

Implements the Repository pattern for clean separation between business logic and data access.
"""

import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from motor.motor_asyncio import AsyncIOMotorCollection

from .database import db_manager
from ..models.mongodb_models import BlogDocument, QuestionDocument, SummaryDocument
from ..core.exceptions import BlogNotFoundException, NoQuestionsFoundException, DatabaseConnectionException

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
    
    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the MongoDB collection."""
        if not db_manager.is_connected:
            raise DatabaseConnectionException("Database not connected")
        return db_manager.get_collection(self.collection_name)


class BlogRepository(BaseRepository):
    """Repository for blog content operations."""
    
    def __init__(self):
        super().__init__('raw_blog_content')
    
    async def find_by_url(self, url: str) -> Optional[BlogDocument]:
        """Find blog by URL with smart matching."""
        try:
            # Try exact match first
            doc = await self.collection.find_one({"url": url})
            if doc:
                return BlogDocument(**doc)
            
            # Try without query parameters
            clean_url = url.split('?')[0].split('#')[0]
            if clean_url != url:
                doc = await self.collection.find_one({"url": clean_url})
                if doc:
                    return BlogDocument(**doc)
            
            # Try domain + path matching for URL variations
            parsed = urlparse(url)
            if parsed.netloc and parsed.path:
                domain_path = f"{parsed.netloc}{parsed.path}"
                doc = await self.collection.find_one({
                    "url": {"$regex": f".*{domain_path.replace('.', r'\.')}.*"}
                })
                if doc:
                    return BlogDocument(**doc)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding blog by URL {url}: {e}")
            raise DatabaseConnectionException(f"Failed to find blog by URL: {e}")
    
    async def find_by_blog_id(self, blog_id: str) -> Optional[BlogDocument]:
        """Find blog by blog_id."""
        try:
            doc = await self.collection.find_one({"blog_id": blog_id})
            return BlogDocument(**doc) if doc else None
        except Exception as e:
            logger.error(f"Error finding blog by ID {blog_id}: {e}")
            raise DatabaseConnectionException(f"Failed to find blog by ID: {e}")
    
    async def find_by_title(self, title: str, fuzzy: bool = False) -> Optional[BlogDocument]:
        """Find blog by title with optional fuzzy matching."""
        try:
            if not fuzzy:
                # Exact title match
                doc = await self.collection.find_one({"title": title})
            else:
                # Fuzzy title matching
                doc = await self.collection.find_one({
                    "title": {"$regex": title[:50], "$options": "i"}
                })
            
            return BlogDocument(**doc) if doc else None
        except Exception as e:
            logger.error(f"Error finding blog by title {title}: {e}")
            raise DatabaseConnectionException(f"Failed to find blog by title: {e}")
    
    async def search_blogs(
        self,
        query: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[BlogDocument]:
        """Search blogs by text query."""
        try:
            cursor = self.collection.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [BlogDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error searching blogs with query {query}: {e}")
            raise DatabaseConnectionException(f"Failed to search blogs: {e}")
    
    async def get_recent_blogs(self, limit: int = 10) -> List[BlogDocument]:
        """Get recently added blogs."""
        try:
            cursor = self.collection.find().sort("created_at", -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [BlogDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting recent blogs: {e}")
            raise DatabaseConnectionException(f"Failed to get recent blogs: {e}")
    
    async def get_blogs_by_domain(self, domain: str, limit: int = 10) -> List[BlogDocument]:
        """Get blogs from a specific domain."""
        try:
            cursor = self.collection.find(
                {"source_domain": domain}
            ).sort("created_at", -1).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [BlogDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting blogs by domain {domain}: {e}")
            raise DatabaseConnectionException(f"Failed to get blogs by domain: {e}")


class SummaryRepository(BaseRepository):
    """Repository for blog summary operations."""
    
    def __init__(self):
        super().__init__('blog_summary')
    
    async def find_by_blog_id(self, blog_id: str) -> Optional[SummaryDocument]:
        """Find summary by blog_id."""
        try:
            doc = await self.collection.find_one({"blog_id": blog_id})
            return SummaryDocument(**doc) if doc else None
        except Exception as e:
            logger.error(f"Error finding summary by blog ID {blog_id}: {e}")
            raise DatabaseConnectionException(f"Failed to find summary: {e}")
    
    async def find_by_topics(
        self,
        topics: List[str],
        limit: int = 10,
        skip: int = 0
    ) -> List[SummaryDocument]:
        """Find summaries by topics."""
        try:
            cursor = self.collection.find(
                {"main_topics": {"$in": topics}}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [SummaryDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error finding summaries by topics {topics}: {e}")
            raise DatabaseConnectionException(f"Failed to find summaries by topics: {e}")
    
    async def get_high_confidence_summaries(
        self,
        min_confidence: float = 0.8,
        limit: int = 10
    ) -> List[SummaryDocument]:
        """Get summaries with high confidence scores."""
        try:
            cursor = self.collection.find(
                {"confidence_score": {"$gte": min_confidence}}
            ).sort("confidence_score", -1).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [SummaryDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting high confidence summaries: {e}")
            raise DatabaseConnectionException(f"Failed to get high confidence summaries: {e}")


class QuestionRepository(BaseRepository):
    """Repository for blog question operations."""
    
    def __init__(self):
        super().__init__('blog_qna')
    
    async def find_by_blog_id(
        self,
        blog_id: str,
        limit: Optional[int] = None,
        skip: int = 0,
        include_inactive: bool = False
    ) -> List[QuestionDocument]:
        """Find questions by blog_id."""
        try:
            # Build query
            query = {"blog_id": blog_id}
            if not include_inactive:
                query["is_active"] = True
            
            # Build cursor with sorting
            cursor = self.collection.find(query).sort("question_order", 1)
            
            # Apply pagination
            if skip > 0:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [QuestionDocument(**doc) for doc in docs]
            
        except Exception as e:
            logger.error(f"Error finding questions by blog ID {blog_id}: {e}")
            raise DatabaseConnectionException(f"Failed to find questions: {e}")
    
    async def count_by_blog_id(self, blog_id: str, include_inactive: bool = False) -> int:
        """Count questions for a blog."""
        try:
            query = {"blog_id": blog_id}
            if not include_inactive:
                query["is_active"] = True
            
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting questions for blog ID {blog_id}: {e}")
            raise DatabaseConnectionException(f"Failed to count questions: {e}")
    
    async def find_by_type(
        self,
        question_type: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[QuestionDocument]:
        """Find questions by type."""
        try:
            cursor = self.collection.find(
                {"question_type": question_type, "is_active": True}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [QuestionDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error finding questions by type {question_type}: {e}")
            raise DatabaseConnectionException(f"Failed to find questions by type: {e}")
    
    async def find_by_difficulty(
        self,
        difficulty_level: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[QuestionDocument]:
        """Find questions by difficulty level."""
        try:
            cursor = self.collection.find(
                {"difficulty_level": difficulty_level, "is_active": True}
            ).sort("question_quality_score", -1).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [QuestionDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error finding questions by difficulty {difficulty_level}: {e}")
            raise DatabaseConnectionException(f"Failed to find questions by difficulty: {e}")
    
    async def get_high_quality_questions(
        self,
        min_quality_score: float = 0.8,
        limit: int = 10,
        skip: int = 0
    ) -> List[QuestionDocument]:
        """Get high quality questions."""
        try:
            cursor = self.collection.find(
                {
                    "question_quality_score": {"$gte": min_quality_score},
                    "is_active": True
                }
            ).sort("question_quality_score", -1).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [QuestionDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting high quality questions: {e}")
            raise DatabaseConnectionException(f"Failed to get high quality questions: {e}")
    
    async def search_questions(
        self,
        query: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[QuestionDocument]:
        """Search questions by text query."""
        try:
            cursor = self.collection.find(
                {
                    "$or": [
                        {"question": {"$regex": query, "$options": "i"}},
                        {"answer": {"$regex": query, "$options": "i"}}
                    ],
                    "is_active": True
                }
            ).sort("question_quality_score", -1).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [QuestionDocument(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error searching questions with query {query}: {e}")
            raise DatabaseConnectionException(f"Failed to search questions: {e}")
    
    async def get_question_statistics(self, blog_id: str) -> Dict[str, Any]:
        """Get statistics for questions of a specific blog."""
        try:
            pipeline = [
                {"$match": {"blog_id": blog_id, "is_active": True}},
                {"$group": {
                    "_id": None,
                    "total_questions": {"$sum": 1},
                    "avg_quality_score": {"$avg": "$question_quality_score"},
                    "question_types": {"$addToSet": "$question_type"},
                    "difficulty_levels": {"$addToSet": "$difficulty_level"},
                    "max_quality_score": {"$max": "$question_quality_score"},
                    "min_quality_score": {"$min": "$question_quality_score"}
                }}
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(length=1)
            
            if result:
                stats = result[0]
                stats.pop('_id', None)  # Remove the _id field
                return stats
            else:
                return {
                    "total_questions": 0,
                    "avg_quality_score": 0,
                    "question_types": [],
                    "difficulty_levels": [],
                    "max_quality_score": 0,
                    "min_quality_score": 0
                }
                
        except Exception as e:
            logger.error(f"Error getting question statistics for blog ID {blog_id}: {e}")
            raise DatabaseConnectionException(f"Failed to get question statistics: {e}")
