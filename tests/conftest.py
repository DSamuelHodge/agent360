"""
Test configuration and shared fixtures for Agent360 tests.
"""
import pytest
import asyncio
import os
from typing import Generator, Any, AsyncGenerator
from datetime import datetime
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.authentication_service import AuthenticationService
from src.workflows.workflow_service import WorkflowService
from tests.fixtures.mock_services import (
    mock_db,
    mock_redis_service,
    mock_event_store,
    mock_model_client,
    mock_settings,
)

# Re-export fixtures
__all__ = [
    'mock_db',
    'mock_redis_service',
    'mock_event_store',
    'mock_model_client',
    'mock_settings',
]

# Performance test configurations
PERF_TEST_DURATION = int(os.getenv('PERF_TEST_DURATION', '60'))  # seconds
PERF_TEST_USERS = int(os.getenv('PERF_TEST_USERS', '10'))  # concurrent users
PERF_TEST_RAMPUP = int(os.getenv('PERF_TEST_RAMPUP', '30'))  # seconds
PERF_TEST_REQUESTS = int(os.getenv('PERF_TEST_REQUESTS', '1000'))  # total requests

# Use pytest-asyncio's event loop
pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope='session')
async def async_session():
    """Create an async session for managing async resources."""
    # Setup
    yield
    # Cleanup

@pytest.fixture
async def test_client(
    mock_db,
    mock_event_store,
    mock_settings
) -> AsyncGenerator[TestClient, None]:
    """Create test client with mocked services."""
    # Setup authentication service
    auth_service = AuthenticationService(mock_db)
    app.dependency_overrides[AuthenticationService] = lambda: auth_service
    
    # Setup workflow service
    workflow_service = WorkflowService(mock_event_store)
    app.dependency_overrides[WorkflowService] = lambda: workflow_service
    
    # Setup test client
    async with TestClient(app) as client:
        yield client
        
    # Cleanup
    app.dependency_overrides.clear()

@pytest.fixture
def performance_config() -> dict:
    """Get performance test configuration."""
    return {
        'duration': PERF_TEST_DURATION,
        'users': PERF_TEST_USERS,
        'rampup': PERF_TEST_RAMPUP,
        'requests': PERF_TEST_REQUESTS
    }

@pytest.fixture
def test_timestamp() -> str:
    """Generate timestamp for test runs."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')

@pytest.fixture
def test_output_dir(test_timestamp: str) -> str:
    """Create and return test output directory."""
    output_dir = os.path.join(
        'test_results',
        test_timestamp
    )
    os.makedirs(output_dir, exist_ok=True)
    return output_dir
