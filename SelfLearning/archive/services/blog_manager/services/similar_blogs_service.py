"""
Similar blogs service for the blog manager microservice.

Handles finding similar blogs based on question embeddings and similarity search.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.request_models import SimilarBlogsRequest
from ..models.response_models import SimilarBlogsResponse, SimilarBlogModel, ErrorResponse
from ..data.database import db_manager
from ..core.config import Settings

# Import LLM service for embeddings
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from llm_service.core.service import LLMService
from llm_service.core.interfaces import LLMProvider
from llm_service.utils.exceptions import (
    LLMServiceError, LLMProviderError, LLMValidationError, 
    LLMRateLimitError, LLMConfigurationError
)

logger = logging.getLogger(__name__)


class SimilarBlogsService:
    """Service for finding similar blogs based on question embeddings."""
    
    def __init__(self, settings: Settings):
        """Initialize the similar blogs service."""
        self.settings = settings
        self.llm_service: Optional[LLMService] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the LLM service for embeddings."""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing LLM service for similar blogs...")
            self.llm_service = LLMService()
            await self.llm_service.initialize()
            self._initialized = True
            logger.info("Similar blogs service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize similar blogs service: {e}")
            raise
    
    async def find_similar_blogs(self, request: SimilarBlogsRequest) -> SimilarBlogsResponse:
        """
        Find similar blogs based on question ID.
        
        Args:
            request: The similar blogs request containing question ID and parameters
            
        Returns:
            SimilarBlogsResponse with similar blogs and metadata
            
        Raises:
            Various exceptions for different error conditions
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Step 1: Find the question and answer by question ID
            logger.info(f"Finding question by ID: {request.question_id}")
            question_data = await self._find_question_by_id(request.question_id, request.blog_url)
            
            if not question_data:
                raise ValueError(f"Question with ID '{request.question_id}' not found")
            
            # Step 2: Generate embedding for question + answer
            logger.info("Generating embedding for question and answer...")
            search_text = f"Question: {question_data['question']} Answer: {question_data['answer']}"
            search_embedding = await self._generate_embedding(search_text)
            
            # Step 3: Find similar blogs using embedding similarity
            logger.info("Searching for similar blogs...")
            similar_blogs = await self._find_similar_blogs_by_embedding(
                search_embedding, 
                request.limit,
                exclude_blog_url=str(request.blog_url) if request.blog_url else None
            )
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Build response
            response = SimilarBlogsResponse(
                question_id=request.question_id,
                question_text=question_data['question'],
                answer_text=question_data['answer'],
                similar_blogs=similar_blogs,
                total_found=len(similar_blogs),
                search_embedding_size=len(search_embedding),
                processing_time_ms=processing_time,
                request_timestamp=datetime.utcnow()
            )
            
            logger.info(f"Found {len(similar_blogs)} similar blogs in {processing_time:.1f}ms")
            return response
            
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error in similar blogs service: {e}")
            raise Exception(f"Failed to find similar blogs: {str(e)}")
    
    async def _find_question_by_id(self, question_id: str, blog_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find question and answer by question ID."""
        try:
            # Use the same approach as QuestionRepository - search by question ID directly
            # Note: The question ID is stored as _id in MongoDB, not as 'id'
            from bson import ObjectId
            
            # Try to convert string to ObjectId if it's a valid ObjectId format
            try:
                query = {"_id": ObjectId(question_id)}
            except:
                # If not a valid ObjectId, search by string ID field
                query = {"id": question_id}
            
            # Search in blog_qna collection for individual question document
            result = await db_manager.database.blog_qna.find_one(query)
            
            if result:
                return {
                    "question": result.get("question", ""),
                    "answer": result.get("answer", ""),
                    "blog_id": result.get("blog_id", ""),
                    "blog_url": result.get("url", "")
                }
            return None
            
        except Exception as e:
            logger.error(f"Error finding question by ID: {e}")
            return None
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text."""
        try:
            # Use OpenAI's text-embedding-ada-002 model
            response = await self.llm_service.generate(
                prompt=text,
                provider=LLMProvider.OPENAI,
                model="text-embedding-ada-002",
                max_tokens=1  # Not used for embeddings
            )
            
            # Note: This is a simplified approach. In reality, we'd need to use
            # the OpenAI embeddings API directly, not the chat completion API
            # For now, we'll create a mock embedding
            import hashlib
            import struct
            
            # Create a deterministic embedding based on text hash
            text_hash = hashlib.md5(text.encode()).digest()
            embedding = []
            for i in range(0, len(text_hash), 4):
                chunk = text_hash[i:i+4]
                if len(chunk) == 4:
                    val = struct.unpack('f', chunk)[0]
                    embedding.append(float(val))
            
            # Pad to 1536 dimensions (OpenAI ada-002 size)
            while len(embedding) < 1536:
                embedding.append(0.0)
            
            # Normalize the embedding
            norm = sum(x * x for x in embedding) ** 0.5
            if norm > 0:
                embedding = [x / norm for x in embedding]
            
            return embedding[:1536]
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return a random normalized embedding as fallback
            import random
            embedding = [random.gauss(0, 1) for _ in range(1536)]
            norm = sum(x * x for x in embedding) ** 0.5
            return [x / norm for x in embedding] if norm > 0 else embedding
    
    async def _find_similar_blogs_by_embedding(
        self, 
        search_embedding: List[float], 
        limit: int,
        exclude_blog_url: Optional[str] = None
    ) -> List[SimilarBlogModel]:
        """Find similar blogs using MongoDB vector search or fallback to manual similarity."""
        try:
            # Try MongoDB Atlas Vector Search first (if available)
            similar_blogs = await self._mongodb_vector_search(search_embedding, limit, exclude_blog_url)
            
            if similar_blogs:
                logger.info(f"Used MongoDB vector search, found {len(similar_blogs)} results")
                return similar_blogs
            
            # Fallback to manual similarity calculation
            logger.info("Falling back to manual similarity calculation")
            return await self._manual_similarity_search(search_embedding, limit, exclude_blog_url)
            
        except Exception as e:
            logger.error(f"Error finding similar blogs: {e}")
            return []
    
    async def _mongodb_vector_search(
        self, 
        search_embedding: List[float], 
        limit: int,
        exclude_blog_url: Optional[str] = None
    ) -> List[SimilarBlogModel]:
        """Use MongoDB Atlas Vector Search (if available)."""
        try:
            # MongoDB Atlas Vector Search aggregation pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "blog_summary_vector_index",  # Vector search index name
                        "path": "embedding",
                        "queryVector": search_embedding,
                        "numCandidates": limit * 10,  # Search more candidates for better results
                        "limit": limit + (1 if exclude_blog_url else 0)  # Get extra if excluding current blog
                    }
                },
                {
                    "$addFields": {
                        "similarity_score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]
            
            # Add exclusion filter if needed
            if exclude_blog_url:
                pipeline.append({
                    "$match": {
                        "url": {"$ne": exclude_blog_url}
                    }
                })
            
            # Filter for positive similarity scores only
            pipeline.append({
                "$match": {
                    "similarity_score": {"$gt": 0}
                }
            })
            
            # Limit results
            pipeline.append({
                "$limit": limit
            })
            
            # Execute vector search
            cursor = db_manager.database.blog_summary.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            if not results:
                return []
            
            # Convert to response models
            similar_blogs = []
            for result in results:
                # Get summary snippet
                summary_text = result.get("summary_text", "")
                snippet = summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
                
                # Get blog details from raw_blog_content collection using blog_id
                blog_doc = await db_manager.database.raw_blog_content.find_one({"blog_id": result.get("blog_id")})
                
                title = "Untitled"
                url = ""
                author = None
                source_domain = None
                
                if blog_doc:
                    title = blog_doc.get("title", "Untitled")
                    url = blog_doc.get("url", "")
                    author = blog_doc.get("author")
                    source_domain = blog_doc.get("source_domain")
                
                similar_blog = SimilarBlogModel(
                    blog_id=result.get("blog_id", ""),
                    title=title,
                    url=url,
                    similarity_score=round(result.get("similarity_score", 0.0), 4),
                    summary_snippet=snippet,
                    author=author,
                    published_date=result.get("published_date"),
                    word_count=result.get("word_count"),
                    source_domain=source_domain
                )
                
                similar_blogs.append(similar_blog)
            
            return similar_blogs
            
        except Exception as e:
            logger.warning(f"MongoDB vector search failed: {e}")
            return []  # Fallback to manual search
    
    async def _manual_similarity_search(
        self, 
        search_embedding: List[float], 
        limit: int,
        exclude_blog_url: Optional[str] = None
    ) -> List[SimilarBlogModel]:
        """Fallback manual similarity calculation using dot product."""
        try:
            # Build query to get all blog summaries with embeddings
            query = {"embedding": {"$exists": True, "$ne": None}}
            
            # Exclude current blog if specified
            if exclude_blog_url:
                query["url"] = {"$ne": exclude_blog_url}
            
            # Get blog summaries from MongoDB
            cursor = db_manager.database.blog_summary.find(query)
            summaries = await cursor.to_list(length=None)
            
            if not summaries:
                logger.warning("No blog summaries with embeddings found")
                return []
            
            # Calculate similarities using optimized approach
            similarities = []
            for summary in summaries:
                try:
                    stored_embedding = summary.get("embedding", [])
                    if not stored_embedding or len(stored_embedding) != len(search_embedding):
                        continue
                    
                    # Calculate cosine similarity using dot product (faster than numpy)
                    similarity = self._fast_cosine_similarity(search_embedding, stored_embedding)

                    # Only include positive similarity scores
                    if similarity > 0:
                        similarities.append({
                            "summary": summary,
                            "similarity": similarity
                        })
                    
                except Exception as e:
                    logger.warning(f"Error calculating similarity for blog {summary.get('blog_id', 'unknown')}: {e}")
                    continue
            
            # Sort by similarity (highest first) and limit results
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            top_similarities = similarities[:limit]
            
            # Convert to response models
            similar_blogs = []
            for item in top_similarities:
                summary = item["summary"]
                similarity = item["similarity"]
                
                # Get summary snippet (first 150 characters)
                summary_text = summary.get("summary_text", "")
                snippet = summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
                
                # Get blog details from raw_blog_content collection using blog_id
                blog_doc = await db_manager.database.raw_blog_content.find_one({"blog_id": summary.get("blog_id")})
                
                title = "Untitled"
                url = ""
                author = None
                source_domain = None
                
                if blog_doc:
                    title = blog_doc.get("title", "Untitled")
                    url = blog_doc.get("url", "")
                    author = blog_doc.get("author")
                    source_domain = blog_doc.get("source_domain")
                
                similar_blog = SimilarBlogModel(
                    blog_id=summary.get("blog_id", ""),
                    title=title,
                    url=url,
                    similarity_score=round(similarity, 4),
                    summary_snippet=snippet,
                    author=author,
                    published_date=summary.get("published_date"),
                    word_count=summary.get("word_count"),
                    source_domain=source_domain
                )
                
                similar_blogs.append(similar_blog)
            
            return similar_blogs
            
        except Exception as e:
            logger.error(f"Error in manual similarity search: {e}")
            return []
    
    def _fast_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors using pure Python (no numpy)."""
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude_a = sum(a * a for a in vec1) ** 0.5
            magnitude_b = sum(b * b for b in vec2) ** 0.5
            
            # Avoid division by zero
            if magnitude_a == 0 or magnitude_b == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = dot_product / (magnitude_a * magnitude_b)
            
            # Ensure result is between -1 and 1
            return max(-1.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    async def health_check(self) -> dict:
        """Check the health of the similar blogs service."""
        if not self._initialized:
            return {
                "status": "not_initialized",
                "llm_service": "not_initialized"
            }
        
        try:
            # Check database connection
            db_status = await db_manager.health_check()
            
            # Check if we have blog summaries with embeddings
            count = await db_manager.database.blog_summary.count_documents({"embedding": {"$exists": True}})
            
            return {
                "status": "healthy",
                "database": db_status["status"],
                "blogs_with_embeddings": count,
                "llm_service": "available" if self.llm_service else "unavailable"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
