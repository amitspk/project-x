"""Question repository for read-only question operations (API service)."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from fyi_widget_api.api.models.schema_models import QuestionAnswerPair

logger = logging.getLogger(__name__)


class QuestionRepository:
    """Repository for read-only question operations (domain-focused name)."""
    
    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        questions_collection: str = "processed_questions",
        blogs_collection: str = "raw_blog_content",
        summaries_collection: str = "blog_summaries"
    ):
        """Initialize repository with database connection."""
        self.database = database
        self.questions_collection = questions_collection
        self.blogs_collection = blogs_collection
        self.summaries_collection = summaries_collection
        logger.info("✅ QuestionRepository initialized")
    
    async def get_questions_by_url(
        self, 
        blog_url: str, 
        limit: Optional[int] = 10
    ) -> List[QuestionAnswerPair]:
        """Get questions for a blog URL. If limit is None, returns all questions."""
        logger.info(f"📖 Getting questions for: {blog_url}")
        
        collection = self.database[self.questions_collection]
        
        cursor = collection.find(
            {"blog_url": blog_url}
        ).sort("created_at", -1)
        
        # Only apply limit if specified
        if limit is not None:
            cursor = cursor.limit(limit)
        
        questions = []
        async for doc in cursor:
            questions.append(QuestionAnswerPair(
                id=str(doc["_id"]),
                question=doc["question"],
                answer=doc["answer"],
                blog_url=doc["blog_url"],
                blog_id=doc.get("blog_id"),
                embedding=doc.get("embedding"),
                created_at=doc["created_at"]
            ))
        
        logger.info(f"✅ Found {len(questions)} questions")
        return questions
    
    async def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific question by ID."""
        try:
            collection = self.database[self.questions_collection]
            question = await collection.find_one({"_id": ObjectId(question_id)})
            return question
        except Exception as e:
            logger.error(f"Error getting question {question_id}: {e}")
            return None
    
    async def increment_question_click_count(self, question_id: str) -> Optional[int]:
        """
        Increment the click count for a question.
        
        Args:
            question_id: The question ID to increment clicks for
            
        Returns:
            The new click count, or None if question not found
        """
        try:
            collection = self.database[self.questions_collection]
            result = await collection.find_one_and_update(
                {"_id": ObjectId(question_id)},
                {
                    "$inc": {"click_count": 1},
                    "$set": {"last_clicked_at": datetime.utcnow()}
                },
                return_document=True  # Return updated document
            )
            
            if result:
                click_count = result.get("click_count", 0)
                logger.debug(f"✅ Incremented click count for question {question_id}: {click_count}")
                return click_count
            else:
                logger.warning(f"⚠️  Question not found for click tracking: {question_id}")
                return None
        except Exception as e:
            logger.error(f"Error incrementing click count for question {question_id}: {e}")
            return None
    
    async def get_blog_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get blog by URL (read-only)."""
        collection = self.database[self.blogs_collection]
        blog = await collection.find_one({"url": url})
        return blog
    
    async def search_similar_blogs(
        self, 
        embedding: List[float], 
        limit: int = 3,
        publisher_domain: Optional[str] = None
    ) -> List:
        """
        Search for similar blogs using embedding similarity.
        
        Uses MongoDB Atlas Vector Search if available, otherwise falls back to Python.
        Note: This method is complex and may be moved to Worker service in the future.
        
        Args:
            embedding: Vector embedding to search for
            limit: Maximum number of results to return
            publisher_domain: Optional domain to filter results (e.g., "example.com")
        """
        logger.info(f"🔍 Searching for similar blogs (limit={limit}, domain={publisher_domain or 'all'})")
        
        try:
            # Try MongoDB Atlas Vector Search
            return await self._vector_search_atlas(embedding, limit, publisher_domain)
        except Exception as e:
            logger.warning(f"Atlas search failed, using fallback: {e}")
            return await self._vector_search_fallback(embedding, limit, publisher_domain)
    
    async def _vector_search_atlas(
        self, 
        embedding: List[float], 
        limit: int,
        publisher_domain: Optional[str] = None
    ) -> List:
        """MongoDB Atlas Vector Search with optional domain filtering."""
        from fyi_widget_api.api.models.schema_models import SimilarBlog
        
        collection = self.database[self.summaries_collection]
        
        # Pre-filter: Get blog URLs matching the domain if provided
        matching_blog_urls = None
        if publisher_domain:
            import re
            
            # Normalize domain (remove www, lowercase)
            domain = publisher_domain.lower().replace("www.", "")
            escaped_domain = re.escape(domain)
            
            # Query blogs collection using MongoDB regex to get URLs matching the domain
            blogs_collection = self.database[self.blogs_collection]
            
            # Create regex pattern to match domain and subdomains in MongoDB
            domain_regex = f"https?://(www\\.)?([a-zA-Z0-9-]+\\.)?{escaped_domain}"
            
            matching_urls = []
            async for blog in blogs_collection.find(
                {"url": {"$regex": domain_regex, "$options": "i"}}, 
                {"url": 1}
            ):
                url = blog.get("url")
                if url:
                    matching_urls.append(url)
            
            if not matching_urls:
                logger.info(f"No blogs found for domain: {publisher_domain}")
                return []
            
            matching_blog_urls = matching_urls
            logger.info(f"Filtering vector search to {len(matching_blog_urls)} blogs for domain: {publisher_domain}")
        
        # Build search stage
        search_stage = {
            "index": "vector_index",
            "knnBeta": {
                "vector": embedding,
                "path": "embedding",
                "k": limit * 3  # Get more to account for filtering
            }
        }
        
        # Add filter if we have matching URLs
        if matching_blog_urls:
            search_stage["filter"] = {
                "blog_url": {"$in": matching_blog_urls}
            }
        
        pipeline = [
            {
                "$search": search_stage
            },
            {
                "$project": {
                    "blog_url": 1,
                    "summary": 1,
                    "score": {"$meta": "searchScore"}
                }
            },
            {"$limit": limit * 2}
        ]
        
        # Collect all blog URLs from search results first
        search_results = []
        async for doc in collection.aggregate(pipeline):
            score = doc.get("score", 0)
            if score > 0:  # Only positive scores
                search_results.append((doc["blog_url"], score))
        
        if not search_results:
            return []
        
        # Batch fetch blog titles for all URLs in a single query
        blog_urls = [url for url, _ in search_results[:limit]]
        blogs_dict = await self._get_blogs_by_urls(blog_urls)
        
        # Build results with titles from batch fetch
        results = []
        for blog_url, score in search_results[:limit]:
            blog = blogs_dict.get(blog_url)
            title = blog.get("title", "Untitled") if blog else "Untitled"
            
            results.append(SimilarBlog(
                url=blog_url,
                title=title,
                similarity_score=score
            ))
        
        return results
    
    async def _vector_search_fallback(
        self, 
        embedding: List[float], 
        limit: int,
        publisher_domain: Optional[str] = None
    ) -> List:
        """Fallback: Python cosine similarity with optional domain filtering."""
        import re
        from fyi_widget_api.api.models.schema_models import SimilarBlog
        
        collection = self.database[self.summaries_collection]
        
        # Build query with domain filter if provided
        query = {"embedding": {"$exists": True, "$ne": None}}
        if publisher_domain:
            # Normalize domain
            domain = publisher_domain.lower().replace("www.", "")
            # Create regex pattern
            domain_pattern = f"https?://(www\\.)?([a-zA-Z0-9-]+\\.)?{re.escape(domain)}"
            query["blog_url"] = {"$regex": domain_pattern, "$options": "i"}
        
        # Get summaries with embeddings and domain filter
        cursor = collection.find(query)
        
        similarities = []
        async for doc in cursor:
            if doc.get("embedding"):
                # Calculate cosine similarity
                sim = self._cosine_similarity(embedding, doc["embedding"])
                if sim > 0:  # Only positive similarities
                    similarities.append((doc["blog_url"], sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = similarities[:limit]
        
        # Batch fetch blog titles for all URLs in a single query
        blog_urls = [url for url, _ in top_results]
        blogs_dict = await self._get_blogs_by_urls(blog_urls)
        
        # Build response with titles from batch fetch
        results = []
        for blog_url, score in top_results:
            blog = blogs_dict.get(blog_url)
            title = blog.get("title", "Untitled") if blog else "Untitled"
            
            results.append(SimilarBlog(
                url=blog_url,
                title=title,
                similarity_score=float(score)
            ))
        
        return results
    
    async def _get_blogs_by_urls(self, urls: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple blogs by URLs in a single query.
        
        Returns a dictionary mapping URL to blog document for efficient lookup.
        """
        if not urls:
            return {}
        
        collection = self.database[self.blogs_collection]
        blogs = {}
        
        # Query all blogs with matching URLs in a single query
        cursor = collection.find({"url": {"$in": urls}})
        async for blog in cursor:
            url = blog.get("url")
            if url:
                blogs[url] = blog
        
        logger.info(f"✅ Fetched {len(blogs)} blogs out of {len(urls)} requested URLs")
        return blogs
    
    async def delete_blog(self, blog_id: str) -> Dict[str, Any]:
        """
        Delete a blog and all related data (questions, summaries).
        
        This is used for admin operations to remove blog content.
        """
        try:
            blog_oid = ObjectId(blog_id)
        except Exception:
            raise ValueError(f"Invalid blog_id format: {blog_id}")
        
        # Get blog URL before deletion (needed for cascading deletes)
        blogs_collection = self.database[self.blogs_collection]
        blog = await blogs_collection.find_one({"_id": blog_oid})
        if not blog:
            raise ValueError(f"Blog not found with id: {blog_id}")
        
        blog_url = blog.get("url")
        
        # Delete from all collections
        deleted_counts = {
            "blog": 0,
            "questions": 0,
            "summary": 0
        }
        
        # Delete blog
        blog_result = await blogs_collection.delete_one({"_id": blog_oid})
        deleted_counts["blog"] = blog_result.deleted_count
        
        # Delete questions
        if blog_url:
            questions_collection = self.database[self.questions_collection]
            questions_result = await questions_collection.delete_many({"blog_url": blog_url})
            deleted_counts["questions"] = questions_result.deleted_count
        
        # Delete summary
        if blog_url:
            summaries_collection = self.database[self.summaries_collection]
            summary_result = await summaries_collection.delete_one({"blog_url": blog_url})
            deleted_counts["summary"] = summary_result.deleted_count
        
        logger.info(f"✅ Deleted blog {blog_id}: {deleted_counts}")
        return {
            "success": True,
            "blog_id": blog_id,
            "deleted": deleted_counts
        }
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
