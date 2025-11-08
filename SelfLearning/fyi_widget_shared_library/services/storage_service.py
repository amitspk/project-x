"""
Storage service for MongoDB operations.

Handles all database read/write operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

# Database manager handled by services
# Configuration handled by service-specific configs
from fyi_widget_shared_library.models.schemas import (
    BlogContentResponse, 
    QuestionAnswerPair, 
    BlogSummary,
    SimilarBlog
)

logger = logging.getLogger(__name__)


class StorageService:
    """Handles all MongoDB storage operations."""
    
    def __init__(
        self,
        database = None,
        blogs_collection: str = "raw_blog_content",
        questions_collection: str = "processed_questions",
        summaries_collection: str = "blog_summaries"
    ):
        self.database = database
        self.blogs_collection = blogs_collection
        self.questions_collection = questions_collection
        self.summaries_collection = summaries_collection
    
    async def save_blog_content(
        self, 
        url: str, 
        title: str, 
        content: str,
        language: str,
        word_count: int,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Save blog content to database.
        
        Returns:
            blog_id: MongoDB ObjectId as string
        """
        logger.info(f"💾 Saving blog content: {url}")
        
        collection = self.database[self.blogs_collection]
        
        # Check if already exists
        existing = await collection.find_one({"url": url})
        if existing:
            logger.info(f"📝 Blog already exists: {url}")
            return str(existing["_id"])
        
        # Create document
        doc = {
            "url": url,
            "title": title,
            "content": content,
            "language": language,
            "word_count": word_count,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await collection.insert_one(doc)
        blog_id = str(result.inserted_id)
        
        logger.info(f"✅ Blog saved: {blog_id}")
        return blog_id
    
    async def save_summary(
        self, 
        blog_id: str, 
        blog_url: str,
        summary_text: str,
        key_points: List[str],
        embedding: List[float],
        title: Optional[str] = None
    ) -> str:
        """
        Save blog summary with embedding.
        
        Args:
            blog_id: Blog ID
            blog_url: Blog URL
            summary_text: Summary text
            key_points: List of key points
            embedding: Vector embedding
            title: Optional LLM-generated title (stored for reference)
        """
        logger.info(f"💾 Saving summary for blog: {blog_id}")
        
        collection = self.database[self.summaries_collection]
        
        doc = {
            "blog_id": blog_id,
            "blog_url": blog_url,
            "summary": summary_text,
            "key_points": key_points,
            "embedding": embedding,
            "created_at": datetime.utcnow()
        }
        
        # Store LLM-generated title if provided (for reference/future use)
        if title:
            doc["llm_title"] = title
        
        result = await collection.insert_one(doc)
        logger.info(f"✅ Summary saved: {result.inserted_id}")
        return str(result.inserted_id)
    
    async def save_questions(
        self, 
        blog_id: str, 
        blog_url: str,
        questions: List[Dict[str, Any]],
        embeddings: List[List[float]] = None
    ) -> List[str]:
        """Save question-answer pairs with embeddings."""
        logger.info(f"💾 Saving {len(questions)} questions for blog: {blog_id}")
        
        collection = self.database[self.questions_collection]
        
        # Prepare documents
        docs = []
        for idx, qa in enumerate(questions):
            doc = {
                "blog_id": blog_id,
                "blog_url": blog_url,
                "question": qa.get("question", ""),
                "answer": qa.get("answer", ""),
                "keyword_anchor": qa.get("keyword_anchor", ""),
                "probability": qa.get("probability"),
                "embedding": embeddings[idx] if embeddings and idx < len(embeddings) else None,
                "click_count": 0,  # Initialize click count to 0
                "created_at": datetime.utcnow()
            }
            docs.append(doc)
        
        if docs:
            result = await collection.insert_many(docs)
            question_ids = [str(id) for id in result.inserted_ids]
            logger.info(f"✅ Questions saved: {len(question_ids)}")
            return question_ids
        
        return []
    
    async def get_blog_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get blog by URL."""
        collection = self.database[self.blogs_collection]
        blog = await collection.find_one({"url": url})
        return blog
    
    async def get_blogs_by_urls(self, urls: List[str]) -> Dict[str, Dict[str, Any]]:
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
    
    async def search_similar_blogs(
        self, 
        embedding: List[float], 
        limit: int = 3,
        publisher_domain: Optional[str] = None
    ) -> List[SimilarBlog]:
        """
        Search for similar blogs using embedding similarity.
        
        Uses MongoDB Atlas Vector Search if available, otherwise falls back to Python.
        
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
    ) -> List[SimilarBlog]:
        """MongoDB Atlas Vector Search with optional domain filtering."""
        collection = self.database[self.summaries_collection]
        
        # Pre-filter: Get blog URLs matching the domain if provided
        matching_blog_urls = None
        if publisher_domain:
            import re
            
            # Normalize domain (remove www, lowercase)
            domain = publisher_domain.lower().replace("www.", "")
            escaped_domain = re.escape(domain)
            
            # Query blogs collection using MongoDB regex to get URLs matching the domain
            # This is much more efficient than fetching all blogs
            blogs_collection = self.database[self.blogs_collection]
            
            # Create regex pattern to match domain and subdomains in MongoDB
            # Matches: https://example.com/*, https://www.example.com/*, https://blog.example.com/*
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
        
        results = []
        async for doc in collection.aggregate(pipeline):
            score = doc.get("score", 0)
            if score > 0:  # Only positive scores
                # Get blog title
                blog = await self.get_blog_by_url(doc["blog_url"])
                title = blog.get("title", "Untitled") if blog else "Untitled"
                
                results.append(SimilarBlog(
                    url=doc["blog_url"],
                    title=title,
                    similarity_score=score
                ))
        
        return results[:limit]
    
    async def _vector_search_fallback(
        self, 
        embedding: List[float], 
        limit: int,
        publisher_domain: Optional[str] = None
    ) -> List[SimilarBlog]:
        """Fallback: Python cosine similarity with optional domain filtering."""
        import numpy as np
        import re
        
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
        
        # Build response
        results = []
        for blog_url, score in top_results:
            blog = await self.get_blog_by_url(blog_url)
            title = blog.get("title", "Untitled") if blog else "Untitled"
            
            results.append(SimilarBlog(
                url=blog_url,
                title=title,
                similarity_score=float(score)
            ))
        
        return results
    
    async def delete_blog(self, blog_id: str) -> Dict[str, Any]:
        """
        Delete a blog and all associated data by blog_id.
        
        Deletes:
        - Blog content from raw_blog_content
        - All questions from processed_questions
        - Summary from blog_summaries
        
        Args:
            blog_id: MongoDB ObjectId of the blog to delete
            
        Returns:
            Dictionary with deletion summary:
            {
                "blog_deleted": bool,
                "questions_deleted": int,
                "summary_deleted": bool,
                "blog_id": str
            }
        """
        logger.info(f"🗑️  Deleting blog and associated data: {blog_id}")
        
        try:
            from bson import ObjectId
            blog_object_id = ObjectId(blog_id)
        except Exception as e:
            logger.error(f"Invalid blog_id format: {blog_id}")
            raise ValueError(f"Invalid blog_id format: {e}")
        
        # Delete blog content
        blogs_collection = self.database[self.blogs_collection]
        blog_result = await blogs_collection.delete_one({"_id": blog_object_id})
        blog_deleted = blog_result.deleted_count > 0
        
        # Delete all questions
        questions_collection = self.database[self.questions_collection]
        questions_result = await questions_collection.delete_many({"blog_id": blog_id})
        questions_deleted = questions_result.deleted_count
        
        # Delete summary
        summaries_collection = self.database[self.summaries_collection]
        summary_result = await summaries_collection.delete_one({"blog_id": blog_id})
        summary_deleted = summary_result.deleted_count > 0
        
        logger.info(
            f"✅ Deletion complete: "
            f"blog={blog_deleted}, "
            f"questions={questions_deleted}, "
            f"summary={summary_deleted}"
        )
        
        return {
            "blog_deleted": blog_deleted,
            "questions_deleted": questions_deleted,
            "summary_deleted": summary_deleted,
            "blog_id": blog_id
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

