"""
MongoDB connection management.

This module provides connection management for MongoDB operations
with proper error handling, connection pooling, and health checks.
"""

import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime

try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None
    AsyncIOMotorCollection = None
    ConnectionFailure = Exception
    ServerSelectionTimeoutError = Exception
    ConfigurationError = Exception
    MongoClient = None

from .settings import MongoDBSettings, ENV_SETTINGS

logger = logging.getLogger(__name__)


class MongoDBConnectionError(Exception):
    """Custom exception for MongoDB connection errors."""
    pass


class MongoDBConnection:
    """
    MongoDB connection manager with async support.
    
    Provides connection management, health checks, and database operations
    for the SelfLearning project.
    """
    
    def __init__(self, settings: Optional[MongoDBSettings] = None):
        """
        Initialize MongoDB connection manager.
        
        Args:
            settings: MongoDB settings. If None, uses environment settings.
        """
        if not MONGODB_AVAILABLE:
            raise ImportError(
                "MongoDB dependencies not installed. "
                "Install with: pip install motor pymongo"
            )
        
        self.settings = settings or ENV_SETTINGS
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected = False
        
        logger.info(f"Initialized MongoDB connection manager for database: {self.settings.database}")
    
    async def connect(self) -> None:
        """
        Establish connection to MongoDB.
        
        Raises:
            MongoDBConnectionError: If connection fails
        """
        try:
            logger.info(f"Connecting to MongoDB at {self.settings.host}:{self.settings.port}")
            
            # Create async client
            connection_string = self.settings.get_connection_string()
            options = self.settings.get_connection_options()
            
            self._client = AsyncIOMotorClient(connection_string, **options)
            
            # Test connection
            await self._client.admin.command('ping')
            
            # Get database
            self._database = self._client[self.settings.database]
            
            self._is_connected = True
            logger.info(f"✅ Successfully connected to MongoDB database: {self.settings.database}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            error_msg = f"Failed to connect to MongoDB: {e}"
            logger.error(error_msg)
            raise MongoDBConnectionError(error_msg) from e
        except ConfigurationError as e:
            error_msg = f"MongoDB configuration error: {e}"
            logger.error(error_msg)
            raise MongoDBConnectionError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error connecting to MongoDB: {e}"
            logger.error(error_msg)
            raise MongoDBConnectionError(error_msg) from e
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            self._is_connected = False
            logger.info("Disconnected from MongoDB")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on MongoDB connection.
        
        Returns:
            Dictionary with health check results
        """
        if not self._is_connected or not self._client:
            return {
                'status': 'disconnected',
                'timestamp': datetime.utcnow().isoformat(),
                'error': 'Not connected to MongoDB'
            }
        
        try:
            # Ping the database
            start_time = datetime.utcnow()
            await self._client.admin.command('ping')
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Get server info
            server_info = await self._client.server_info()
            
            return {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'response_time_seconds': response_time,
                'server_version': server_info.get('version'),
                'database': self.settings.database,
                'host': self.settings.host,
                'port': self.settings.port
            }
            
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """
        Get a collection from the database.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            AsyncIOMotorCollection instance
            
        Raises:
            MongoDBConnectionError: If not connected
        """
        if not self._is_connected or self._database is None:
            raise MongoDBConnectionError("Not connected to MongoDB")
        
        return self._database[collection_name]
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """
        Get the database instance.
        
        Returns:
            AsyncIOMotorDatabase instance
            
        Raises:
            MongoDBConnectionError: If not connected
        """
        if not self._is_connected or self._database is None:
            raise MongoDBConnectionError("Not connected to MongoDB")
        
        return self._database
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to MongoDB."""
        return self._is_connected
    
    async def create_indexes(self) -> None:
        """Create necessary indexes for optimal performance."""
        if not self._is_connected or self._database is None:
            raise MongoDBConnectionError("Not connected to MongoDB")
        
        try:
            logger.info("Creating MongoDB indexes...")
            
            # Content metadata indexes
            content_collection = self.get_collection('content_metadata')
            await content_collection.create_index('content_id', unique=True)
            await content_collection.create_index('url')
            await content_collection.create_index('title')
            await content_collection.create_index('created_at')
            await content_collection.create_index([('title', 'text'), ('summary', 'text')])
            
            # User interactions indexes
            interactions_collection = self.get_collection('user_interactions')
            await interactions_collection.create_index('content_id')
            await interactions_collection.create_index('interaction_type')
            await interactions_collection.create_index('timestamp')
            
            # Search analytics indexes
            analytics_collection = self.get_collection('search_analytics')
            await analytics_collection.create_index('query')
            await analytics_collection.create_index('timestamp')
            await analytics_collection.create_index('result_count')
            
            # Processing jobs indexes
            jobs_collection = self.get_collection('processing_jobs')
            await jobs_collection.create_index('job_id', unique=True)
            await jobs_collection.create_index('status')
            await jobs_collection.create_index('created_at')
            await jobs_collection.create_index('content_id')
            
            logger.info("✅ MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create MongoDB indexes: {e}")
            raise MongoDBConnectionError(f"Index creation failed: {e}") from e
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        if not self._is_connected or self._database is None:
            raise MongoDBConnectionError("Not connected to MongoDB")
        
        try:
            stats = await self._database.command('dbStats')
            
            # Get collection stats
            collections = await self._database.list_collection_names()
            collection_stats = {}
            
            for collection_name in collections:
                collection = self.get_collection(collection_name)
                count = await collection.count_documents({})
                collection_stats[collection_name] = {
                    'document_count': count
                }
            
            return {
                'database_name': self.settings.database,
                'collections': len(collections),
                'data_size': stats.get('dataSize', 0),
                'storage_size': stats.get('storageSize', 0),
                'index_size': stats.get('indexSize', 0),
                'collection_stats': collection_stats,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise MongoDBConnectionError(f"Stats retrieval failed: {e}") from e
    
    @asynccontextmanager
    async def get_session(self):
        """
        Get a MongoDB session for transactions.
        
        Usage:
            async with connection.get_session() as session:
                # Use session for operations
                pass
        """
        if not self._client:
            raise MongoDBConnectionError("Not connected to MongoDB")
        
        async with await self._client.start_session() as session:
            yield session


# Global connection instance
_global_connection: Optional[MongoDBConnection] = None


async def get_connection() -> MongoDBConnection:
    """
    Get global MongoDB connection instance.
    
    Returns:
        MongoDBConnection instance
    """
    global _global_connection
    
    if _global_connection is None:
        _global_connection = MongoDBConnection()
        await _global_connection.connect()
    
    return _global_connection


async def close_connection() -> None:
    """Close global MongoDB connection."""
    global _global_connection
    
    if _global_connection:
        await _global_connection.disconnect()
        _global_connection = None
