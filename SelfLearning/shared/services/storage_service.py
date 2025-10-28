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
from shared.models.schemas import (
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
        embedding: List[float]
    ) -> str:
        """Save blog summary with embedding."""
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
                "icon": qa.get("icon", "💡"),
                "embedding": embeddings[idx] if embeddings and idx < len(embeddings) else None,
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
                icon=doc.get("icon", "💡"),
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
    
    async def search_similar_blogs(
        self, 
        embedding: List[float], 
        limit: int = 3
    ) -> List[SimilarBlog]:
        """
        Search for similar blogs using embedding similarity.
        
        Uses MongoDB Atlas Vector Search if available, otherwise falls back to Python.
        """
        logger.info(f"🔍 Searching for similar blogs (limit={limit})")
        
        try:
            # Try MongoDB Atlas Vector Search
            return await self._vector_search_atlas(embedding, limit)
        except Exception as e:
            logger.warning(f"Atlas search failed, using fallback: {e}")
            return await self._vector_search_fallback(embedding, limit)
    
    async def _vector_search_atlas(
        self, 
        embedding: List[float], 
        limit: int
    ) -> List[SimilarBlog]:
        """MongoDB Atlas Vector Search."""
        collection = self.database[self.summaries_collection]
        
        pipeline = [
            {
                "$search": {
                    "index": "vector_index",
                    "knnBeta": {
                        "vector": embedding,
                        "path": "embedding",
                        "k": limit * 2  # Get more to filter
                    }
                }
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
        limit: int
    ) -> List[SimilarBlog]:
        """Fallback: Python cosine similarity."""
        import numpy as np
        
        collection = self.database[self.summaries_collection]
        
        # Get all summaries with embeddings
        cursor = collection.find({"embedding": {"$exists": True, "$ne": None}})
        
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

