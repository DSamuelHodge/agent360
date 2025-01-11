"""
Rate limiting middleware for Agent360.
Implements token bucket algorithm with Redis backend.
"""
from typing import Optional, Tuple
import time
import logging
from fastapi import Request, HTTPException
from redis import Redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    tokens_per_second: float
    bucket_size: int
    key_prefix: str = "ratelimit"

class RateLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, redis: Redis, config: RateLimitConfig):
        self.redis = redis
        self.config = config
        
    async def _get_tokens(self, key: str) -> Tuple[int, float]:
        """Get current tokens and last update time."""
        pipeline = self.redis.pipeline()
        pipeline.hget(key, "tokens")
        pipeline.hget(key, "last_update")
        tokens, last_update = pipeline.execute()
        
        return (
            int(tokens) if tokens else self.config.bucket_size,
            float(last_update) if last_update else time.time()
        )
        
    async def _update_tokens(self, key: str, tokens: int, last_update: float):
        """Update tokens and last update time."""
        pipeline = self.redis.pipeline()
        pipeline.hset(key, "tokens", tokens)
        pipeline.hset(key, "last_update", last_update)
        pipeline.execute()
        
    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Unique identifier for the rate limit bucket
            
        Returns:
            True if request is allowed, False otherwise
        """
        try:
            key = f"{self.config.key_prefix}:{identifier}"
            
            # Get current state
            tokens, last_update = await self._get_tokens(key)
            
            # Calculate token replenishment
            now = time.time()
            time_passed = now - last_update
            new_tokens = min(
                self.config.bucket_size,
                tokens + time_passed * self.config.tokens_per_second
            )
            
            # Check if we have enough tokens
            if new_tokens < 1:
                return False
                
            # Update state
            await self._update_tokens(key, new_tokens - 1, now)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            return True  # Allow request on error
            
class RateLimitMiddleware:
    """Middleware for rate limiting."""
    
    def __init__(
        self,
        redis: Redis,
        config: RateLimitConfig,
        get_identifier=lambda r: r.client.host
    ):
        self.limiter = RateLimiter(redis, config)
        self.get_identifier = get_identifier
        
    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""
        identifier = self.get_identifier(request)
        
        # Check rate limit
        if not await self.limiter.check_rate_limit(identifier):
            logger.warning(f"Rate limit exceeded for {identifier}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
            
        return await call_next(request)
        
def configure_rate_limiting(app, redis: Redis, config: RateLimitConfig):
    """Configure rate limiting for FastAPI app."""
    middleware = RateLimitMiddleware(redis, config)
    app.middleware("http")(middleware)
