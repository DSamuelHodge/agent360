from pydantic_settings import BaseSettings
from functools import lru_cache

class AuthSettings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        env_prefix = "AUTH_"

@lru_cache()
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
