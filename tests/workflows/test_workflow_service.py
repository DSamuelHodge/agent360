"""Tests for workflow service."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.agent_runtime.context import AgentContext, AgentState
from src.agent_runtime.reasoning import ReasoningEngine
from src.infrastructure.event_store import EventStore
from src.workflows.workflow_service import WorkflowService

@pytest.fixture
def mock_db():
    """Mock database connection."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value={"status": "success"})
    return db

@pytest.fixture
def mock_event_store():
    """Mock event store."""
    event_store = AsyncMock(spec=EventStore)
    event_store.store_event = AsyncMock()
    event_store.list_workflows = AsyncMock(return_value=[])
    return event_store

@pytest.fixture
def sample_context():
    """Sample agent context."""
    state = AgentState(
        tenant_id="test_tenant",
        variables={
            "session_id": "test_session",
            "user_id": "test_user"
        }
    )
    return AgentContext(
        state=state,
        model_config={
            "model": "gpt-4",
            "temperature": 0.7
        },
        tool_config={
            "max_retries": 3,
            "timeout": 30
        },
        workflow_config={},
        tenant_config=None
    )

@pytest.fixture
def workflow_service(mock_db, mock_event_store):
    """Create workflow service instance."""
    service = WorkflowService(db=mock_db, event_store=mock_event_store)
    return service

@pytest.mark.asyncio
async def test_execute_workflow(workflow_service, sample_context):
    """Test executing a workflow."""
    workflow_id = str(uuid4())
    user_id = "test_user"
    
    result = await workflow_service.execute_workflow(workflow_id, user_id)
    
    assert result is not None
    assert result["workflow_id"] == workflow_id

@pytest.mark.asyncio
async def test_get_workflow_status(workflow_service):
    """Test getting workflow status."""
    workflow_id = str(uuid4())
    user_id = "test_user"
    
    status = await workflow_service.get_workflow_status(workflow_id, user_id)
    
    assert status is not None

@pytest.mark.asyncio
async def test_workflow_error_handling(workflow_service, sample_context):
    """Test workflow error handling."""
    workflow_id = str(uuid4())
    user_id = "test_user"
    
    # Mock database error
    workflow_service.db.execute.side_effect = Exception("Database error")
    
    with pytest.raises(Exception) as exc:
        await workflow_service.execute_workflow(workflow_id, user_id)
    
    assert str(exc.value) == "Database error"

@pytest.mark.asyncio
async def test_workflow_timeout(workflow_service, sample_context):
    """Test workflow timeout handling."""
    workflow_id = str(uuid4())
    user_id = "test_user"
    
    # Mock slow database operation
    async def slow_operation(*args, **kwargs):
        await asyncio.sleep(0.2)
        return {}
    
    workflow_service.db.execute.side_effect = slow_operation
    
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            workflow_service.execute_workflow(workflow_id, user_id),
            timeout=0.1
        )

@pytest.mark.asyncio
async def test_start_workflow(workflow_service, sample_context):
    """Test starting a workflow."""
    workflow_id = await workflow_service.start_workflow(
        context=sample_context,
        prompt="test prompt"
    )
    
    assert workflow_id is not None
    workflow_service.event_store.store_event.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_workflow(workflow_service):
    """Test canceling a workflow."""
    workflow_id = uuid4()
    
    await workflow_service.cancel_workflow(workflow_id)
    
    workflow_service.event_store.store_event.assert_called_once()

@pytest.mark.asyncio
async def test_list_workflows(workflow_service):
    """Test listing workflows."""
    tenant_id = "test_tenant"
    
    workflows = await workflow_service.list_workflows(tenant_id)
    
    assert isinstance(workflows, list)
    workflow_service.event_store.list_workflows.assert_called_once_with(tenant_id)

@pytest.mark.asyncio
async def test_workflow_retry(workflow_service):
    """Test workflow retry."""
    workflow_id = uuid4()
    
    result = await workflow_service.retry_workflow(workflow_id)
    
    assert result is True
