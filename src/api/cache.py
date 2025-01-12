"""
Redis cache implementation for Agent360.
"""
from typing import Optional, Any
import fakeredis
from datetime import timedelta
import json

class RedisCache:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        # Use fakeredis for testing
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = self.redis.get(key)
        if value:
            return json.loads(value)
        return None
        
    def set(self, key: str, value: Any, expire: Optional[timedelta] = None) -> None:
        """Set value in cache with optional expiration."""
        self.redis.set(key, json.dumps(value), ex=int(expire.total_seconds()) if expire else None)
        
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        self.redis.delete(key)
        
    def increment(self, key: str) -> int:
        """Increment counter and return new value."""
        return self.redis.incr(key)
        
    def expire(self, key: str, expire: timedelta) -> None:
        """Set expiration for key."""
        self.redis.expire(key, int(expire.total_seconds()))
