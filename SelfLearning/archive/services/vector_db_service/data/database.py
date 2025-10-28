"""
Database connection management for Vector DB Service.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

from ..core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connections."""
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected: bool = False
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        if self._is_connected:
            return
        
        try:
            logger.info(f"Connecting to MongoDB: {settings.mongodb_url}")
            
            self._client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size
            )
            
            # Test connection
            await self._client.admin.command('ping')
            
            self._database = self._client[settings.mongodb_database]
            self._is_connected = True
            
            logger.info(f"✅ Connected to MongoDB: {settings.mongodb_database}")
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self._is_connected = False
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._is_connected = False
            logger.info("Disconnected from MongoDB")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        if not self._is_connected or self._client is None:
            return {
                'status': 'disconnected',
                'error': 'Not connected to MongoDB'
            }
        
        try:
            await self._client.admin.command('ping')
            
            # Try to get collection counts (skip if authentication issues)
            try:
                if self._database is not None:
                    blogs_count = await self._database[settings.blog_collection].estimated_document_count()
                    questions_count = await self._database[settings.question_collection].estimated_document_count()
                else:
                    blogs_count = 0
                    questions_count = 0
            except Exception:
                # If we can't get counts, just report connected
                blogs_count = -1
                questions_count = -1
            
            return {
                'status': 'healthy',
                'database': settings.mongodb_database,
                'collections': {
                    'blogs': blogs_count if blogs_count >= 0 else "N/A",
                    'questions': questions_count if questions_count >= 0 else "N/A"
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get a collection by name."""
        if not self._is_connected or not self._database:
            raise RuntimeError("Database not connected")
        return self._database[name]
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._is_connected
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if not self._database:
            raise RuntimeError("Database not connected")
        return self._database


# Global database manager instance
db_manager = DatabaseManager()

