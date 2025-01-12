"""
Rate limiting middleware for Agent360.
"""
from typing import Callable, Dict
from fastapi import Request, HTTPException, status
from datetime import timedelta
from .cache import RedisCache

class RateLimiter:
    def __init__(
        self,
        cache: RedisCache,
        rate_limit: int = 100,  # requests
        time_window: int = 60,  # seconds
    ):
        self.cache = cache
        self.rate_limit = rate_limit
        self.time_window = time_window
        
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ):
        # Get client IP
        client_ip = request.client.host
        
        # Create rate limit key
        key = f"rate_limit:{client_ip}:{request.url.path}"
        
        # Check rate limit
        requests = self.cache.increment(key)
        if requests == 1:
            self.cache.expire(key, timedelta(seconds=self.time_window))
            
        if requests > self.rate_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
            
        response = await call_next(request)
        return response
