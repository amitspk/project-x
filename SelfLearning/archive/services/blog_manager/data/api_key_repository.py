"""
Repository for API key database operations.

Handles CRUD operations for API keys in MongoDB.
"""

import logging
from typing import Optional, List
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from ..core.auth import APIKey, APIKeyStatus, APIKeyScope
from ..core.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class APIKeyRepository:
    """
    Repository for API key data access.
    
    Collection: api_keys
    Indexes:
    - key_id (unique)
    - status + expires_at (for cleanup)
    - last_used_at (for analytics)
    """
    
    COLLECTION_NAME = "api_keys"
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Initialize repository.
        
        Args:
            database: MongoDB database instance
        """
        self.db = database
        self.collection = database[self.COLLECTION_NAME]
    
    async def create_indexes(self):
        """Create necessary indexes for the collection."""
        try:
            indexes = [
                IndexModel([("key_id", ASCENDING)], unique=True, name="key_id_unique"),
                IndexModel([("status", ASCENDING)], name="status_idx"),
                IndexModel(
                    [("status", ASCENDING), ("expires_at", ASCENDING)],
                    name="status_expiry_idx"
                ),
                IndexModel([("created_at", DESCENDING)], name="created_at_idx"),
                IndexModel([("last_used_at", DESCENDING)], name="last_used_idx"),
            ]
            
            await self.collection.create_indexes(indexes)
            logger.info(f"Created indexes for {self.COLLECTION_NAME}")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise DatabaseException(f"Index creation failed: {e}")
    
    async def create(self, api_key: APIKey) -> APIKey:
        """
        Store a new API key.
        
        Args:
            api_key: API key model
            
        Returns:
            Created API key
            
        Raises:
            DatabaseException: If creation fails
        """
        try:
            # Convert to dict, excluding None values
            key_dict = api_key.model_dump(exclude_none=True)
            
            # Convert enums to strings
            key_dict['scopes'] = [str(scope.value) for scope in api_key.scopes]
            key_dict['status'] = api_key.status.value
            
            await self.collection.insert_one(key_dict)
            
            logger.info(f"Created API key: {api_key.key_id}")
            return api_key
            
        except DuplicateKeyError:
            raise DatabaseException(f"API key {api_key.key_id} already exists")
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            raise DatabaseException(f"Failed to create API key: {e}")
    
    async def find_by_key_id(self, key_id: str) -> Optional[APIKey]:
        """
        Find API key by its ID.
        
        Args:
            key_id: Unique key identifier
            
        Returns:
            API key model or None if not found
        """
        try:
            doc = await self.collection.find_one({"key_id": key_id})
            
            if not doc:
                return None
            
            # Convert back to model
            return self._doc_to_model(doc)
            
        except Exception as e:
            logger.error(f"Failed to find API key {key_id}: {e}")
            return None
    
    async def find_by_hashed_key(self, hashed_key: str) -> Optional[APIKey]:
        """
        Find API key by its hash (for lookups during auth).
        
        Note: This is not efficient. In practice, you'd store a key_hash
        index or use a key ID in the header. This is for demonstration.
        
        Args:
            hashed_key: Hashed API key
            
        Returns:
            API key model or None
        """
        try:
            doc = await self.collection.find_one({"hashed_key": hashed_key})
            
            if not doc:
                return None
            
            return self._doc_to_model(doc)
            
        except Exception as e:
            logger.error(f"Failed to find API key by hash: {e}")
            return None
    
    async def find_all_active(self, limit: int = 100) -> List[APIKey]:
        """
        Find all active API keys.
        
        Args:
            limit: Maximum number of keys to return
            
        Returns:
            List of active API keys
        """
        try:
            cursor = self.collection.find(
                {"status": APIKeyStatus.ACTIVE.value}
            ).limit(limit).sort("created_at", DESCENDING)
            
            keys = []
            async for doc in cursor:
                keys.append(self._doc_to_model(doc))
            
            return keys
            
        except Exception as e:
            logger.error(f"Failed to find active keys: {e}")
            return []
    
    async def update(self, api_key: APIKey) -> bool:
        """
        Update an existing API key.
        
        Args:
            api_key: Updated API key model
            
        Returns:
            True if updated, False otherwise
        """
        try:
            key_dict = api_key.model_dump(exclude_none=True)
            key_dict['scopes'] = [str(scope.value) for scope in api_key.scopes]
            key_dict['status'] = api_key.status.value
            
            # Remove key_id from update (it's the query)
            key_id = key_dict.pop('key_id')
            
            result = await self.collection.update_one(
                {"key_id": key_id},
                {"$set": key_dict}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated API key: {key_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update API key: {e}")
            return False
    
    async def revoke(self, key_id: str) -> bool:
        """
        Revoke an API key (soft delete).
        
        Args:
            key_id: Key ID to revoke
            
        Returns:
            True if revoked, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"key_id": key_id},
                {
                    "$set": {
                        "status": APIKeyStatus.REVOKED.value,
                        "revoked_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Revoked API key: {key_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
            return False
    
    async def delete(self, key_id: str) -> bool:
        """
        Permanently delete an API key (hard delete).
        
        Args:
            key_id: Key ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.collection.delete_one({"key_id": key_id})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted API key: {key_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete API key: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """
        Clean up expired keys by marking them as EXPIRED.
        
        Returns:
            Number of keys marked as expired
        """
        try:
            result = await self.collection.update_many(
                {
                    "status": APIKeyStatus.ACTIVE.value,
                    "expires_at": {"$lt": datetime.utcnow()}
                },
                {
                    "$set": {"status": APIKeyStatus.EXPIRED.value}
                }
            )
            
            count = result.modified_count
            if count > 0:
                logger.info(f"Marked {count} expired API keys")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired keys: {e}")
            return 0
    
    async def get_usage_stats(self) -> dict:
        """
        Get API key usage statistics.
        
        Returns:
            Dictionary with usage stats
        """
        try:
            stats = {
                "total": await self.collection.count_documents({}),
                "active": await self.collection.count_documents(
                    {"status": APIKeyStatus.ACTIVE.value}
                ),
                "revoked": await self.collection.count_documents(
                    {"status": APIKeyStatus.REVOKED.value}
                ),
                "expired": await self.collection.count_documents(
                    {"status": APIKeyStatus.EXPIRED.value}
                ),
            }
            
            # Most used keys
            cursor = self.collection.find(
                {"status": APIKeyStatus.ACTIVE.value}
            ).sort("usage_count", DESCENDING).limit(5)
            
            most_used = []
            async for doc in cursor:
                most_used.append({
                    "key_id": doc["key_id"],
                    "name": doc["name"],
                    "usage_count": doc.get("usage_count", 0)
                })
            
            stats["most_used"] = most_used
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}
    
    def _doc_to_model(self, doc: dict) -> APIKey:
        """
        Convert MongoDB document to APIKey model.
        
        Args:
            doc: MongoDB document
            
        Returns:
            APIKey model
        """
        # Convert string scopes back to enum
        if 'scopes' in doc:
            doc['scopes'] = [APIKeyScope(s) for s in doc['scopes']]
        
        # Convert status back to enum
        if 'status' in doc:
            doc['status'] = APIKeyStatus(doc['status'])
        
        # Remove MongoDB _id
        doc.pop('_id', None)
        
        return APIKey(**doc)

