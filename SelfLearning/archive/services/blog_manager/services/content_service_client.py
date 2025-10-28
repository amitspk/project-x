"""
Client for Content Processing Service.

Handles all communication with the consolidated content service.
"""

import logging
from typing import List, Dict, Any, Optional
import httpx

from ..core.config import Settings

logger = logging.getLogger(__name__)


class ContentServiceClient:
    """Client for Content Processing Service API."""
    
    def __init__(self, settings: Settings):
        self.base_url = settings.content_service_url
        self.timeout = 120.0  # Content processing can take time
        self.client = httpx.AsyncClient(timeout=self.timeout)
        logger.info(f"✅ Content Service Client initialized: {self.base_url}")
    
    async def process_blog(
        self,
        url: str,
        num_questions: int = 5,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Process a blog URL.
        
        This triggers the complete pipeline:
        - Crawling
        - Summary generation
        - Question generation
        - Embeddings (all in parallel!)
        - Storage
        """
        logger.info(f"📤 Requesting blog processing: {url}")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/processing/process",
                json={
                    "url": url,
                    "num_questions": num_questions,
                    "force_refresh": force_refresh
                }
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Blog processed: {url}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Processing failed with status {e.response.status_code}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Processing request failed: {e}")
            raise
    
    async def process_blog_async(
        self,
        url: str,
        num_questions: int = 5,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Process a blog asynchronously (returns immediately).
        """
        logger.info(f"📤 Requesting async blog processing: {url}")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/processing/process-async",
                json={
                    "url": url,
                    "num_questions": num_questions,
                    "force_refresh": force_refresh
                }
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Async processing started: {url}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Async processing request failed: {e}")
            raise
    
    async def get_questions_by_url(
        self,
        blog_url: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get questions for a blog URL."""
        logger.info(f"📤 Getting questions for: {blog_url}")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/questions/by-url",
                params={
                    "blog_url": blog_url,
                    "limit": limit
                }
            )
            response.raise_for_status()
            
            questions = response.json()
            logger.info(f"✅ Retrieved {len(questions)} questions")
            return questions
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"No questions found for: {blog_url}")
                return []
            logger.error(f"❌ Failed to get questions: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Request failed: {e}")
            raise
    
    async def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific question by ID."""
        logger.info(f"📤 Getting question: {question_id}")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/questions/{question_id}"
            )
            response.raise_for_status()
            
            question = response.json()
            logger.info(f"✅ Retrieved question: {question_id}")
            return question
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Question not found: {question_id}")
                return None
            logger.error(f"❌ Failed to get question: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Request failed: {e}")
            raise
    
    async def search_similar_blogs(
        self,
        question_id: str,
        limit: int = 3
    ) -> Dict[str, Any]:
        """Search for similar blogs based on a question."""
        logger.info(f"📤 Searching similar blogs for question: {question_id}")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/search/similar",
                json={
                    "question_id": question_id,
                    "limit": limit
                }
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Found {len(result.get('similar_blogs', []))} similar blogs")
            return result
            
        except Exception as e:
            logger.error(f"❌ Similarity search failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of Content Processing Service."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

