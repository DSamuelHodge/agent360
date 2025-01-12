"""Configuration settings for Agent360."""
import os
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Database settings
    cassandra_hosts: List[str] = ["localhost"]
    cassandra_port: int = 9042
    cassandra_keyspace: str = "agent360"
    cassandra_username: Optional[str] = None
    cassandra_password: Optional[str] = None
    
    # JWT settings
    jwt_secret_key: str = "your-secret-key-here"  # Change in production
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    
    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # API settings
    api_version: str = "v1"
    api_prefix: str = "/api/v1"
    debug: bool = True
    
    class Config:
        """Pydantic config."""
        env_prefix = "AGENT360_"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
