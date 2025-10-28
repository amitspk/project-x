"""
Redis caching service for API Gateway.

Caches frequently accessed data to reduce latency and database load.
"""

import logging
import json
from typing import Optional, Any
import redis.asyncio as redis

from ..core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service."""
    
    def __init__(self):
        self.redis_url = settings.redis_url
        self.ttl = settings.cache_ttl_seconds
        self._client: Optional[redis.Redis] = None
        self._enabled = settings.enable_cache
        
        if not self._enabled:
            logger.warning("⚠️  Caching is disabled")
    
    async def connect(self):
        """Connect to Redis."""
        if not self._enabled:
            return
        
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._client.ping()
            logger.info(f"✅ Redis connected: {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self._enabled = False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            logger.info("Redis disconnected")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._enabled or not self._client:
            return None
        
        try:
            value = await self._client.get(key)
            if value:
                logger.debug(f"✅ Cache hit: {key}")
                return json.loads(value)
            logger.debug(f"❌ Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self._enabled or not self._client:
            return False
        
        try:
            ttl = ttl or self.ttl
            serialized = json.dumps(value)
            await self._client.setex(key, ttl, serialized)
            logger.debug(f"✅ Cached: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._enabled or not self._client:
            return False
        
        try:
            await self._client.delete(key)
            logger.debug(f"🗑️  Cache deleted: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        if not self._enabled or not self._client:
            return 0
        
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self._client.delete(*keys)
                logger.info(f"🗑️  Cleared {deleted} cache entries matching: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    def make_key(self, *parts: str) -> str:
        """Generate a cache key from parts."""
        return ":".join(str(p) for p in parts)


# Global cache service instance
cache_service = CacheService()

