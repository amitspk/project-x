"""
Database connection and management for the blog manager microservice.

Handles MongoDB connection lifecycle, health checks, and connection pooling.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, OperationFailure

from ..core.config import settings
from ..core.exceptions import DatabaseConnectionException

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connections and database operations."""
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected: bool = False
        self._connection_start_time: Optional[datetime] = None
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        if self._is_connected and self._client is not None:
            logger.info("Already connected to MongoDB")
            return
        
        try:
            logger.info(f"Connecting to MongoDB at {settings.mongodb_host}:{settings.mongodb_port}")
            
            self._client = AsyncIOMotorClient(
                settings.mongodb_url,
                serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size,
                retryWrites=True,
                retryReads=True
            )
            
            # Test the connection
            await self._client.admin.command('ping')
            
            self._database = self._client[settings.mongodb_database]
            self._is_connected = True
            self._connection_start_time = datetime.utcnow()
            
            logger.info(f"✅ Successfully connected to MongoDB database: {settings.mongodb_database}")
            
            # Create indexes for optimal performance
            await self._create_indexes()
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"❌ MongoDB server selection timed out: {e}")
            await self._cleanup_connection()
            raise DatabaseConnectionException(f"Server selection timeout: {e}")
        
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            await self._cleanup_connection()
            raise DatabaseConnectionException(f"Connection failure: {e}")
        
        except OperationFailure as e:
            logger.error(f"❌ MongoDB authentication failed: {e}")
            await self._cleanup_connection()
            raise DatabaseConnectionException(f"Authentication failure: {e}")
        
        except Exception as e:
            logger.error(f"❌ Unexpected MongoDB connection error: {e}")
            await self._cleanup_connection()
            raise DatabaseConnectionException(f"Unexpected error: {e}")
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            await self._cleanup_connection()
            logger.info("Disconnected from MongoDB")
    
    async def _cleanup_connection(self) -> None:
        """Clean up connection state."""
        self._is_connected = False
        self._client = None
        self._database = None
        self._connection_start_time = None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        if not self._is_connected or self._client is None:
            return {
                'status': 'disconnected',
                'timestamp': datetime.utcnow().isoformat(),
                'error': 'Not connected to MongoDB'
            }
        
        try:
            # Test connection with ping
            start_time = datetime.utcnow()
            await self._client.admin.command('ping')
            ping_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Get database stats
            db_stats = await self._database.command('dbStats')
            
            # Calculate uptime
            uptime_seconds = None
            if self._connection_start_time:
                uptime_seconds = (datetime.utcnow() - self._connection_start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'database_name': settings.mongodb_database,
                'ping_time_ms': round(ping_time, 2),
                'uptime_seconds': uptime_seconds,
                'collections_count': db_stats.get('collections', 0),
                'data_size_mb': round(db_stats.get('dataSize', 0) / (1024 * 1024), 2),
                'storage_size_mb': round(db_stats.get('storageSize', 0) / (1024 * 1024), 2)
            }
        
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """Get a collection from the database."""
        if not self._is_connected or self._database is None:
            raise DatabaseConnectionException("Not connected to MongoDB")
        
        return self._database[collection_name]
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if not self._is_connected or self._database is None:
            raise DatabaseConnectionException("Not connected to MongoDB")
        
        return self._database
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to MongoDB."""
        return self._is_connected
    
    async def _create_indexes(self) -> None:
        """Create necessary indexes for optimal performance."""
        try:
            logger.info("Creating MongoDB indexes...")
            
            # Raw blog content indexes
            raw_content_collection = self.get_collection('raw_blog_content')
            await raw_content_collection.create_index('blog_id', unique=True)
            await raw_content_collection.create_index('url')
            await raw_content_collection.create_index('title')
            await raw_content_collection.create_index('source_domain')
            await raw_content_collection.create_index('created_at')
            await raw_content_collection.create_index([('title', 'text'), ('content', 'text')])
            
            # Blog summary indexes
            summary_collection = self.get_collection('blog_summary')
            await summary_collection.create_index('blog_id', unique=True)
            await summary_collection.create_index('main_topics')
            await summary_collection.create_index('created_at')
            await summary_collection.create_index('confidence_score')
            
            # Blog Q&A indexes
            qna_collection = self.get_collection('blog_qna')
            await qna_collection.create_index('blog_id')
            await qna_collection.create_index([('blog_id', 1), ('question_order', 1)])
            await qna_collection.create_index('question_type')
            await qna_collection.create_index('difficulty_level')
            await qna_collection.create_index('created_at')
            await qna_collection.create_index('is_active')
            
            logger.info("✅ MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create MongoDB indexes: {e}")
            # Don't raise exception here as indexes are not critical for basic functionality
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        if not self._is_connected or self._database is None:
            raise DatabaseConnectionException("Not connected to MongoDB")
        
        try:
            # Get database stats
            db_stats = await self._database.command('dbStats')
            
            # Get collection stats
            collections_stats = {}
            collection_names = ['raw_blog_content', 'blog_summary', 'blog_qna']
            
            for collection_name in collection_names:
                try:
                    collection = self.get_collection(collection_name)
                    count = await collection.count_documents({})
                    
                    if count > 0:
                        coll_stats = await self._database.command('collStats', collection_name)
                        collections_stats[collection_name] = {
                            'count': count,
                            'size_mb': round(coll_stats.get('size', 0) / (1024 * 1024), 2),
                            'avg_obj_size_bytes': coll_stats.get('avgObjSize', 0),
                            'indexes': coll_stats.get('nindexes', 0),
                            'index_size_mb': round(coll_stats.get('totalIndexSize', 0) / (1024 * 1024), 2)
                        }
                    else:
                        collections_stats[collection_name] = {
                            'count': 0,
                            'size_mb': 0,
                            'avg_obj_size_bytes': 0,
                            'indexes': 0,
                            'index_size_mb': 0
                        }
                except Exception as e:
                    logger.warning(f"Failed to get stats for collection {collection_name}: {e}")
                    collections_stats[collection_name] = {'error': str(e)}
            
            return {
                'database_name': settings.mongodb_database,
                'total_size_mb': round(db_stats.get('dataSize', 0) / (1024 * 1024), 2),
                'storage_size_mb': round(db_stats.get('storageSize', 0) / (1024 * 1024), 2),
                'collections': collections_stats,
                'uptime_seconds': (datetime.utcnow() - self._connection_start_time).total_seconds() if self._connection_start_time else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            raise DatabaseConnectionException(f"Failed to retrieve database stats: {e}")


# Global database manager instance
db_manager = DatabaseManager()
