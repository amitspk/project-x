"""
MongoDB Vector-enabled content processor.

This module integrates MongoDB vector capabilities with the existing
content processing pipeline, replacing ChromaDB with MongoDB for vector storage.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import numpy as np
from datetime import datetime

# Import MongoDB module
try:
    from mongodb.config.connection import MongoDBConnection
    from mongodb.config.settings import MongoDBSettings
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

logger = logging.getLogger(__name__)


class MongoDBVectorContentProcessor:
    """
    MongoDB-based vector content processor.
    
    Replaces ChromaDB with MongoDB for vector storage and semantic search.
    """
    
    def __init__(
        self,
        database_name: str = "blog_ai_db",
        collection_name: str = "blog_summary",
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize MongoDB vector content processor.
        
        Args:
            database_name: MongoDB database name
            collection_name: Collection to store vectors in
            openai_api_key: OpenAI API key for embeddings
        """
        if not MONGODB_AVAILABLE:
            raise Exception("MongoDB module not available. Install: pip install motor pymongo")
        
        self.database_name = database_name
        self.collection_name = collection_name
        self._openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.mongodb_connection: Optional[MongoDBConnection] = None
        self._initialized = False
        
        if not self._openai_api_key:
            logger.warning("No OpenAI API key provided. Embedding generation will fail.")
    
    async def initialize(self):
        """Initialize MongoDB connection"""
        if self._initialized:
            return
        
        settings = MongoDBSettings()
        settings.database = self.database_name
        
        self.mongodb_connection = MongoDBConnection(settings)
        await self.mongodb_connection.connect()
        
        logger.info(f"✅ MongoDB Vector Processor initialized for {self.database_name}.{self.collection_name}")
        self._initialized = True
    
    async def cleanup(self):
        """Clean up MongoDB connection"""
        if self.mongodb_connection:
            await self.mongodb_connection.disconnect()
            self._initialized = False
            logger.info("🔌 MongoDB connection closed")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            import openai
            
            response = await openai.embeddings.acreate(
                model="text-embedding-ada-002",
                input=text
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def index_content(
        self,
        content: str,
        metadata: Dict[str, Any],
        content_id: str
    ) -> str:
        """
        Index content with vector embedding in MongoDB.
        
        Args:
            content: Text content to index
            metadata: Associated metadata
            content_id: Unique identifier for the content
            
        Returns:
            Document ID of the indexed content
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate embedding
            embedding = await self.generate_embedding(content)
            
            # Prepare document
            doc = {
                "content_id": content_id,
                "content": content,
                "embedding": embedding,
                "embedding_model": "text-embedding-ada-002",
                "embedding_provider": "openai",
                "embedding_dimensions": len(embedding),
                "embedding_generated_at": datetime.now(),
                "metadata": metadata,
                "indexed_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Store in MongoDB
            collection = self.mongodb_connection.get_collection(self.collection_name)
            
            # Upsert based on content_id
            result = await collection.replace_one(
                {"content_id": content_id},
                doc,
                upsert=True
            )
            
            doc_id = str(result.upserted_id) if result.upserted_id else "updated"
            logger.info(f"✅ Indexed content: {content_id} (ID: {doc_id})")
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to index content {content_id}: {e}")
            raise
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            a = np.array(vec1)
            b = np.array(vec2)
            
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return float(dot_product / (norm_a * norm_b))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    async def search_similar_content(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content using vector similarity.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            metadata_filter: Optional metadata filters
            
        Returns:
            List of similar content with similarity scores
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            
            # Build MongoDB filter
            mongo_filter = {"embedding": {"$exists": True, "$ne": None}}
            if metadata_filter:
                for key, value in metadata_filter.items():
                    mongo_filter[f"metadata.{key}"] = value
            
            # Get all documents with embeddings
            collection = self.mongodb_connection.get_collection(self.collection_name)
            cursor = collection.find(mongo_filter)
            
            results = []
            async for doc in cursor:
                try:
                    # Calculate similarity
                    similarity = self.cosine_similarity(query_embedding, doc['embedding'])
                    
                    if similarity >= similarity_threshold:
                        # Remove embedding from result for readability
                        result_doc = {k: v for k, v in doc.items() if k != 'embedding'}
                        result_doc['similarity_score'] = similarity
                        results.append(result_doc)
                        
                except Exception as e:
                    logger.warning(f"Error processing document {doc.get('content_id', 'unknown')}: {e}")
                    continue
            
            # Sort by similarity score (descending)
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Return top results
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def get_content_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get content by ID"""
        if not self._initialized:
            await self.initialize()
        
        collection = self.mongodb_connection.get_collection(self.collection_name)
        doc = await collection.find_one({"content_id": content_id})
        
        if doc:
            # Remove embedding for readability
            return {k: v for k, v in doc.items() if k != 'embedding'}
        
        return None
    
    async def delete_content(self, content_id: str) -> bool:
        """Delete content by ID"""
        if not self._initialized:
            await self.initialize()
        
        collection = self.mongodb_connection.get_collection(self.collection_name)
        result = await collection.delete_one({"content_id": content_id})
        
        return result.deleted_count > 0
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self._initialized:
            await self.initialize()
        
        collection = self.mongodb_connection.get_collection(self.collection_name)
        
        total_docs = await collection.count_documents({})
        docs_with_embeddings = await collection.count_documents({"embedding": {"$exists": True, "$ne": None}})
        
        return {
            "total_documents": total_docs,
            "documents_with_embeddings": docs_with_embeddings,
            "embedding_coverage": (docs_with_embeddings / total_docs * 100) if total_docs > 0 else 0,
            "collection_name": self.collection_name,
            "database_name": self.database_name
        }
    
    async def update_content_metadata(self, content_id: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for existing content"""
        if not self._initialized:
            await self.initialize()
        
        collection = self.mongodb_connection.get_collection(self.collection_name)
        result = await collection.update_one(
            {"content_id": content_id},
            {
                "$set": {
                    "metadata": metadata,
                    "updated_at": datetime.now()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def reindex_content(self, content_id: str) -> bool:
        """Regenerate embedding for existing content"""
        if not self._initialized:
            await self.initialize()
        
        # Get existing content
        collection = self.mongodb_connection.get_collection(self.collection_name)
        doc = await collection.find_one({"content_id": content_id})
        
        if not doc or not doc.get('content'):
            logger.error(f"Content not found: {content_id}")
            return False
        
        try:
            # Generate new embedding
            new_embedding = await self.generate_embedding(doc['content'])
            
            # Update document
            result = await collection.update_one(
                {"content_id": content_id},
                {
                    "$set": {
                        "embedding": new_embedding,
                        "embedding_dimensions": len(new_embedding),
                        "embedding_generated_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                }
            )
            
            logger.info(f"✅ Reindexed content: {content_id}")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to reindex content {content_id}: {e}")
            return False


# Compatibility alias for existing code
VectorContentProcessor = MongoDBVectorContentProcessor
