"""
Test configuration and shared fixtures for Agent360 tests.
"""
import pytest
import asyncio
import os
from typing import Generator, Any
from datetime import datetime

# Performance test configurations
PERFORMANCE_CONFIG = {
    "auth": {
        "users": 100,
        "spawn_rate": 10,
        "run_time": "5m",
        "host": "http://localhost:8000"
    },
    "workflow": {
        "users": 50,
        "spawn_rate": 5,
        "run_time": "10m",
        "host": "http://localhost:8000"
    }
}

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, None]:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def performance_config() -> dict:
    """Get performance test configuration."""
    return PERFORMANCE_CONFIG

@pytest.fixture(scope="session")
def test_timestamp() -> str:
    """Generate timestamp for test runs."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

@pytest.fixture(scope="session")
def test_output_dir(test_timestamp: str) -> str:
    """Create and return test output directory."""
    output_dir = os.path.join(
        "tests",
        "results",
        f"performance_{test_timestamp}"
    )
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def pytest_configure(config):
    """Configure test markers."""
    config.addinivalue_line(
        "markers",
        "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers",
        "load_test: mark test as a load test"
    )
    config.addinivalue_line(
        "markers",
        "stress_test: mark test as a stress test"
    )
    config.addinivalue_line(
        "markers",
        "endurance_test: mark test as an endurance test"
    )
    config.addinivalue_line(
        "markers",
        "spike_test: mark test as a spike test"
    )

import pytest
import redis
from typing import AsyncGenerator

from src.infrastructure.model_client import ModelClient
from src.infrastructure.redis_client import RedisClient
from src.auth.authentication_service import AuthenticationService

@pytest.fixture
async def model_client() -> ModelClient:
    return ModelClient(api_key="test_key", model="gpt-4")

@pytest.fixture
async def redis_client() -> RedisClient:
    client = redis.Redis(host='localhost', port=6379, db=0)
    yield RedisClient(client)
    client.close()

@pytest.fixture
def auth_service() -> AuthenticationService:
    return AuthenticationService(
        secret_key="test_secret_key",
        algorithm="HS256"
    )
