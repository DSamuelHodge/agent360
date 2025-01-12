"""
Redis client service for Agent360.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from redis import Redis, ConnectionPool
from prometheus_client import Counter, Histogram
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Metrics
CACHE_HITS = Counter(
    'redis_cache_hits_total',
    'Total number of cache hits',
    ['operation']
)
CACHE_MISSES = Counter(
    'redis_cache_misses_total',
    'Total number of cache misses',
    ['operation']
)
OPERATION_LATENCY = Histogram(
    'redis_operation_latency_seconds',
    'Operation latency in seconds',
    ['operation']
)

class RedisClient:
    """Redis client with monitoring and connection pooling."""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        max_connections: int = 10,
        socket_timeout: int = 5,
        retry_on_timeout: bool = True
    ):
        """Initialize Redis client.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Optional Redis password
            ssl: Use SSL connection
            max_connections: Maximum number of connections
            socket_timeout: Socket timeout in seconds
            retry_on_timeout: Retry on timeout
        """
        self.pool = ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            retry_on_timeout=retry_on_timeout,
            decode_responses=True
        )
        self.client = Redis(connection_pool=self.pool)
    
    async def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Get value from Redis.
        
        Args:
            key: Key to get
            default: Default value if key doesn't exist
            
        Returns:
            Value or default if key doesn't exist
        """
        with tracer.start_as_current_span('redis.get') as span:
            span.set_attribute('redis.key', key)
            
            with OPERATION_LATENCY.labels('get').time():
                try:
                    value = self.client.get(key)
                    if value is not None:
                        CACHE_HITS.labels('get').inc()
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            return value
                    
                    CACHE_MISSES.labels('get').inc()
                    return default
                    
                except Exception as e:
                    logger.error(f"Redis GET error: {e}")
                    span.record_exception(e)
                    return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in Redis.
        
        Args:
            key: Key to set
            value: Value to set
            ttl: Optional TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        with tracer.start_as_current_span('redis.set') as span:
            span.set_attribute('redis.key', key)
            
            with OPERATION_LATENCY.labels('set').time():
                try:
                    if not isinstance(value, (str, bytes)):
                        value = json.dumps(value)
                    
                    if ttl is not None:
                        return bool(self.client.setex(key, ttl, value))
                    return bool(self.client.set(key, value))
                    
                except Exception as e:
                    logger.error(f"Redis SET error: {e}")
                    span.record_exception(e)
                    return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis.
        
        Args:
            key: Key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        with tracer.start_as_current_span('redis.delete') as span:
            span.set_attribute('redis.key', key)
            
            with OPERATION_LATENCY.labels('delete').time():
                try:
                    return bool(self.client.delete(key))
                except Exception as e:
                    logger.error(f"Redis DELETE error: {e}")
                    span.record_exception(e)
                    return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis.
        
        Args:
            key: Key to check
            
        Returns:
            True if key exists, False otherwise
        """
        with OPERATION_LATENCY.labels('exists').time():
            try:
                return bool(self.client.exists(key))
            except Exception as e:
                logger.error(f"Redis EXISTS error: {e}")
                return False
    
    async def incr(
        self,
        key: str,
        amount: int = 1
    ) -> Optional[int]:
        """Increment key by amount.
        
        Args:
            key: Key to increment
            amount: Amount to increment by
            
        Returns:
            New value or None if error
        """
        with OPERATION_LATENCY.labels('incr').time():
            try:
                return self.client.incrby(key, amount)
            except Exception as e:
                logger.error(f"Redis INCR error: {e}")
                return None
    
    async def decr(
        self,
        key: str,
        amount: int = 1
    ) -> Optional[int]:
        """Decrement key by amount.
        
        Args:
            key: Key to decrement
            amount: Amount to decrement by
            
        Returns:
            New value or None if error
        """
        with OPERATION_LATENCY.labels('decr').time():
            try:
                return self.client.decrby(key, amount)
            except Exception as e:
                logger.error(f"Redis DECR error: {e}")
                return None
    
    async def expire(
        self,
        key: str,
        seconds: int
    ) -> bool:
        """Set key expiration.
        
        Args:
            key: Key to set expiration on
            seconds: Seconds until expiration
            
        Returns:
            True if successful, False otherwise
        """
        with OPERATION_LATENCY.labels('expire').time():
            try:
                return bool(self.client.expire(key, seconds))
            except Exception as e:
                logger.error(f"Redis EXPIRE error: {e}")
                return False
    
    async def ttl(self, key: str) -> int:
        """Get key TTL.
        
        Args:
            key: Key to get TTL for
            
        Returns:
            TTL in seconds, -2 if key doesn't exist,
            -1 if key has no TTL
        """
        with OPERATION_LATENCY.labels('ttl').time():
            try:
                return self.client.ttl(key)
            except Exception as e:
                logger.error(f"Redis TTL error: {e}")
                return -2
    
    def close(self) -> None:
        """Close Redis connection pool."""
        self.pool.disconnect()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()
