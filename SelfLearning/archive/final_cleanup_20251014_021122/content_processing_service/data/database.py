"""
MongoDB connection manager for Content Processing Service.

Handles all database connections and operations in one place.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

from ..core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connections and provides access to collections."""
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected = False
        self._connection_time: Optional[datetime] = None
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        if self._is_connected and self._client:
            logger.info("Already connected to MongoDB")
            return
        
        try:
            logger.info(f"Connecting to MongoDB: {settings.mongodb_url}")
            
            self._client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size,
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            await self._client.admin.command('ping')
            
            self._database = self._client[settings.mongodb_database]
            self._is_connected = True
            self._connection_time = datetime.utcnow()
            
            logger.info(f"✅ Connected to MongoDB: {settings.mongodb_database}")
            
            # Create indexes for performance
            await self._create_indexes()
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to MongoDB: {e}")
            self._is_connected = False
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._is_connected = False
            self._connection_time = None
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        try:
            # Try to create indexes, but don't fail if we can't
            try:
                await self._database[settings.blogs_collection].create_index("url", unique=True)
                await self._database[settings.blogs_collection].create_index("created_at")
            except Exception:
                pass
            
            try:
                await self._database[settings.questions_collection].create_index("blog_url")
                await self._database[settings.questions_collection].create_index("blog_id")
                await self._database[settings.questions_collection].create_index([("blog_url", 1), ("created_at", -1)])
            except Exception:
                pass
            
            try:
                await self._database[settings.summaries_collection].create_index("blog_id")
                await self._database[settings.summaries_collection].create_index("blog_url")
            except Exception:
                pass
            
            logger.info("✅ Database indexes created/verified")
            
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        if not self._is_connected or self._client is None:
            return {
                'status': 'disconnected',
                'error': 'Not connected to MongoDB'
            }
        
        try:
            # Ping database
            await self._client.admin.command('ping')
            
            # Get collection counts
            try:
                blogs_count = await self._database[settings.blogs_collection].estimated_document_count()
                questions_count = await self._database[settings.questions_collection].estimated_document_count()
                summaries_count = await self._database[settings.summaries_collection].estimated_document_count()
            except Exception:
                blogs_count = -1
                questions_count = -1
                summaries_count = -1
            
            uptime_seconds = (datetime.utcnow() - self._connection_time).total_seconds() if self._connection_time else 0
            
            return {
                'status': 'healthy',
                'database': settings.mongodb_database,
                'uptime_seconds': int(uptime_seconds),
                'collections': {
                    'blogs': blogs_count if blogs_count >= 0 else "N/A",
                    'questions': questions_count if questions_count >= 0 else "N/A",
                    'summaries': summaries_count if summaries_count >= 0 else "N/A"
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get a collection by name."""
        if not self._is_connected or self._database is None:
            raise RuntimeError("Database not connected")
        return self._database[name]
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if self._database is None:
            raise RuntimeError("Database not connected")
        return self._database
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._is_connected


# Global database manager instance
db_manager = DatabaseManager()

