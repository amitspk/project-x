"""Database manager for MongoDB connection."""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MongoDB connection and database access."""
    
    def __init__(self):
        """Initialize database manager."""
        self.client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        logger.info("🔧 DatabaseManager initialized")
    
    async def connect(
        self,
        mongodb_url: str = "mongodb://localhost:27017",
        database_name: str = "blog_qa_db",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Connect to MongoDB.
        
        Args:
            mongodb_url: MongoDB connection URL
            database_name: Name of the database
            username: MongoDB username
            password: MongoDB password
        """
        try:
            # Build connection string with auth if provided
            if username and password:
                # Extract host and port from mongodb_url
                if "://" in mongodb_url:
                    protocol, rest = mongodb_url.split("://", 1)
                    # Remove any existing auth
                    if "@" in rest:
                        rest = rest.split("@", 1)[1]
                    connection_url = f"{protocol}://{username}:{password}@{rest}"
                else:
                    connection_url = f"mongodb://{username}:{password}@{mongodb_url}"
            else:
                connection_url = mongodb_url
            
            self.client = AsyncIOMotorClient(connection_url)
            self._database = self.client[database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            
            logger.info(f"✅ Connected to MongoDB: {database_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if self._database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._database
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            if self._database is not None:
                await self.client.admin.command('ping')
                
                # Try to count collections
                collections = await self._database.list_collection_names()
                
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("👋 Database connection closed")
