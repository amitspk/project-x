"""
Repository for blog_meta_data collection.

This collection tracks request counts and metadata for threshold checking.
Each blog URL has one entry that tracks how many times it has been requested
for processing (before questions exist).
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import ReturnDocument
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class BlogMetadataRepository:
    """Repository for managing blog metadata (request tracking for threshold)."""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Initialize blog metadata repository.
        
        Args:
            database: MongoDB database instance
        """
        self.database = database
        self.collection = database["blog_meta_data"]
    
    async def create_indexes(self):
        """Create indexes for blog_meta_data collection."""
        # PRIMARY: Unique index on URL
        await self.collection.create_index("url", unique=True)
        
        # ANALYTICS: Query by publisher and time
        await self.collection.create_index([("publisher_id", 1), ("updated_at", -1)])
        
        logger.info("✅ Created indexes for blog_meta_data")
    
    async def increment_and_get_count(
        self, 
        *, 
        url: str, 
        publisher_id: str
    ) -> int:
        """
        Atomically increment request count and return new value.
        
        This is called every time check-and-load is called for a blog
        that doesn't have questions yet.
        
        Creates entry if doesn't exist (upsert).
        
        Args:
            url: Normalized blog URL
            publisher_id: Publisher ID (for analytics, not uniqueness)
            
        Returns:
            New request_count value after increment
        """
        now = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            {"url": url},
            {
                "$inc": {"request_count": 1},
                "$set": {
                    "last_requested_at": now,
                    "updated_at": now
                },
                "$setOnInsert": {
                    "publisher_id": publisher_id,
                    "first_requested_at": now,
                    "created_at": now
                }
            },
            upsert=True,  # Create if doesn't exist
            return_document=ReturnDocument.AFTER
        )
        
        new_count = result["request_count"]
        logger.info(f"📊 Request count incremented for {url}: {new_count}")
        return new_count
    
    async def get_count(self, *, url: str) -> int:
        """
        Get current request count for a URL.
        
        Args:
            url: Normalized blog URL
            
        Returns:
            Current request_count, or 0 if entry doesn't exist
        """
        doc = await self.collection.find_one({"url": url})
        return doc["request_count"] if doc else 0
    
    async def get_metadata(self, *, url: str) -> Optional[Dict[str, Any]]:
        """
        Get complete metadata entry for a URL.
        
        Args:
            url: Normalized blog URL
            
        Returns:
            Metadata document or None if not found
        """
        return await self.collection.find_one({"url": url})
    
    async def reset_count(self, *, url: str) -> bool:
        """
        Reset request count to 0 for a URL.
        
        Useful for admin operations or cleanup.
        
        Args:
            url: Normalized blog URL
            
        Returns:
            True if document was updated, False if not found
        """
        result = await self.collection.update_one(
            {"url": url},
            {
                "$set": {
                    "request_count": 0,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        success = result.modified_count > 0
        if success:
            logger.info(f"✅ Reset request count for: {url}")
        return success
    
    async def delete_by_url(self, *, url: str) -> bool:
        """
        Delete metadata entry for a URL.
        
        Args:
            url: Normalized blog URL
            
        Returns:
            True if document was deleted
        """
        result = await self.collection.delete_one({"url": url})
        success = result.deleted_count > 0
        if success:
            logger.info(f"✅ Deleted metadata for: {url}")
        return success
    
    async def get_stats_by_publisher(self, *, publisher_id: str, limit: int = 100) -> list:
        """
        Get request statistics for a publisher.
        
        Args:
            publisher_id: Publisher ID
            limit: Maximum number of results
            
        Returns:
            List of blog metadata entries for this publisher
        """
        cursor = self.collection.find(
            {"publisher_id": publisher_id}
        ).sort("updated_at", -1).limit(limit)
        
        return await cursor.to_list(length=limit)

