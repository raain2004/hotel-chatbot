"""Redis cache service for Claude responses and rate limiting."""
import json
import redis.asyncio as redis
from typing import Any, Optional
from datetime import timedelta

from app.config import settings


class RedisCache:
    """Async Redis cache wrapper."""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=getattr(settings, 'redis_host', 'localhost'),
                port=getattr(settings, 'redis_port', 6379),
                db=0,
                decode_responses=True,
            )
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None
    
    async def set(self, key: str, value: Any, expire: timedelta = timedelta(minutes=30)) -> bool:
        """Set value in cache with expiration."""
        try:
            await self.client.setex(key, int(expire.total_seconds()), json.dumps(value))
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.client.exists(key) > 0
        except Exception:
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()


# Global cache instance
cache = RedisCache()


async def get_cache() -> RedisCache:
    """Dependency to get cache instance."""
    return cache
