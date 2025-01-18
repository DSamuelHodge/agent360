"""
Mock services for testing external dependencies.
"""
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio

class MockDatabaseConnection:
    """Mock database connection for testing."""
    def __init__(self):
        self.connected = False
        self.execute = AsyncMock()
        self.fetch_one = AsyncMock()
        self.fetch_all = AsyncMock()
        self.transaction = AsyncMock()
        
    async def connect(self):
        """Connect to database."""
        self.connected = True
        
    async def disconnect(self):
        """Disconnect from database."""
        self.connected = False
        
    async def is_connected(self):
        """Check if connected."""
        return self.connected

class MockRedisService:
    """Mock Redis service for testing."""
    def __init__(self):
        self.data: Dict[str, Any] = {}
        
    async def get(self, key: str) -> Any:
        return self.data.get(key)
        
    async def set(self, key: str, value: Any, ex: int = None) -> None:
        self.data[key] = value
        
    async def delete(self, key: str) -> None:
        if key in self.data:
            del self.data[key]
            
    async def exists(self, key: str) -> bool:
        return key in self.data

class MockEventStore:
    """Mock event store for testing."""
    def __init__(self):
        self.events: Dict[str, list] = {}
        
    async def append_event(self, stream_id: str, event_type: str, event_data: Dict[str, Any]) -> None:
        if stream_id not in self.events:
            self.events[stream_id] = []
        self.events[stream_id].append({
            "type": event_type,
            "data": event_data
        })
        
    async def get_events(self, stream_id: str) -> list:
        return self.events.get(stream_id, [])
        
    async def get_latest_event(self, stream_id: str) -> Dict[str, Any]:
        events = self.events.get(stream_id, [])
        return events[-1] if events else None

class MockModelClient:
    """Mock model client for testing."""
    def __init__(self):
        self.generate = AsyncMock()
        self.stream = AsyncMock()
        self.embeddings = AsyncMock()
        
        # Setup default responses
        self.default_responses = {
            "chain_of_thought": {
                "status": "success",
                "output": "Mock model response",
                "analysis": "Mock analysis",
                "tool_result": {"status": "success"},
                "tool_config": {"max_tokens": 100, "temperature": 0.7},
                "state": {"workflow_id": "test_workflow", "step_id": "step_1"}
            },
            "reflective": {
                "status": "success",
                "output": "Mock model response",
                "iterations": 3,
                "reflection": "Mock reflection",
                "improved_result": "Mock improved result",
                "final_result": "Mock final result",
                "tool_result": {"status": "success"},
                "tool_config": {"max_tokens": 100, "temperature": 0.7},
                "state": {"workflow_id": "test_workflow", "step_id": "step_1"}
            }
        }
        
        self.generate.return_value = self.default_responses["chain_of_thought"]
        
    async def setup_responses(self, responses: Dict[str, Any]) -> None:
        """Setup mock responses for different prompts."""
        self.generate.side_effect = lambda prompt, **kwargs: responses.get(prompt, self.default_responses["chain_of_thought"])
        
    async def setup_stream_responses(self, responses: Dict[str, Any]) -> None:
        """Setup mock streaming responses."""
        self.stream.side_effect = lambda prompt, **kwargs: iter(responses.get(prompt, []))
        
    def set_workflow_type(self, workflow_type: str) -> None:
        """Set the type of workflow responses."""
        if workflow_type in self.default_responses:
            self.generate.return_value = self.default_responses[workflow_type]

class MockTemporalService:
    """Mock Temporal service for testing."""
    def __init__(self):
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.connect = AsyncMock()
        self.start_worker = AsyncMock()
        self.close = AsyncMock()
        
    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        task_queue: str = 'test-queue'
    ) -> Dict[str, Any]:
        """Execute a workflow."""
        # Check if workflow is cancelled
        if workflow_id in self.workflows and self.workflows[workflow_id]["status"] == "cancelled":
            raise asyncio.CancelledError()
            
        # Simulate workflow execution
        workflow_result = {
            "status": "success",
            "output": "Mock workflow output",
            "tool_results": [
                {
                    "status": "success",
                    "result": "Mock tool result"
                }
            ]
        }
        
        # Handle error cases
        if input_data.get("tools") == ["error_tool"]:
            workflow_result = {
                "status": "error",
                "error": {
                    "message": "Mock error",
                    "recovery_attempted": True
                }
            }
            
        # Handle tool execution
        elif input_data.get("tools") and input_data.get("params"):
            workflow_result["tool_results"] = [
                {
                    "status": "success",
                    "result": input_data["params"].get("test", "default")
                }
            ]
        
        self.workflows[workflow_id] = workflow_result
        return workflow_result
    
    async def get_workflow_state(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow state."""
        return self.workflows.get(workflow_id, {
            "status": "not_found"
        })
        
    async def cancel_workflow(self, workflow_id: str) -> None:
        """Cancel a workflow."""
        if workflow_id in self.workflows:
            self.workflows[workflow_id]["status"] = "cancelled"

@pytest.fixture
def mock_db() -> MockDatabaseConnection:
    """Mock database connection fixture."""
    return MockDatabaseConnection()

@pytest.fixture
def mock_redis_service() -> MockRedisService:
    """Mock Redis service fixture."""
    return MockRedisService()

@pytest.fixture
def mock_event_store() -> MockEventStore:
    """Mock event store fixture."""
    return MockEventStore()

@pytest.fixture
def mock_model_client() -> MockModelClient:
    """Mock model client fixture."""
    return MockModelClient()

@pytest.fixture
async def mock_temporal_service() -> MockTemporalService:
    """Fixture for mock temporal service."""
    service = MockTemporalService()
    await service.connect()
    await service.start_worker()
    yield service
    await service.close()

@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock settings fixture."""
    return MagicMock(
        DATABASE_URL="mock://localhost:5432/testdb",
        REDIS_URL="mock://localhost:6379",
        SECRET_KEY="test_secret_key",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
    )
