"""Tests for agent workflow."""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

from temporalio.common import RetryPolicy

from src.agent_runtime.context import AgentContext, AgentState
from src.agent_runtime.reasoning import ReasoningEngine
from src.workflows.agent_workflow import AgentWorkflow

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
def agent_workflow():
    """Create agent workflow instance."""
    workflow = AgentWorkflow()
    workflow._execute_reasoning = AsyncMock(return_value={
        "tool_selection": {
            "name": "test_tool",
            "params": {"key": "value"}
        }
    })
    workflow._execute_tool = AsyncMock(return_value={
        "status": "success",
        "result": "test result"
    })
    workflow._process_result = AsyncMock(return_value={
        "status": "success",
        "result": "test result"
    })
    return workflow

@pytest.mark.asyncio
async def test_workflow_initialization(agent_workflow, sample_context):
    """Test workflow initialization."""
    with patch('temporalio.workflow.execute_activity') as mock_activity:
        mock_activity.return_value = sample_context.state

        result = await agent_workflow.run(sample_context)

        assert result is not None
        assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_workflow_error_handling(agent_workflow, sample_context):
    """Test workflow error handling."""
    with patch('temporalio.workflow.execute_activity') as mock_activity:
        mock_activity.side_effect = Exception("Test error")

        with pytest.raises(Exception) as exc:
            await agent_workflow.run(sample_context)

        assert str(exc.value) == "Test error"

@pytest.mark.asyncio
async def test_workflow_retry_policy(agent_workflow, sample_context):
    """Test workflow retry policy."""
    # Mock the update_state activity to simulate retries
    call_count = 0

    async def mock_execute_activity(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:  # Fail first 3 times
            await asyncio.sleep(0.1)  # Simulate retry delay
            raise Exception("Temporary error")
        return sample_context.state

    # Create a mock for execute_activity that will fail 3 times then succeed
    mock_activity = AsyncMock()
    mock_activity.side_effect = mock_execute_activity

    with patch('temporalio.workflow.execute_activity', mock_activity):
        # Mock retry policy - match the actual implementation
        retry_policy = RetryPolicy(
            initial_interval=1,
            backoff_coefficient=2.0,
            maximum_interval=5,
            maximum_attempts=5
        )
        agent_workflow._retry_policy = retry_policy

        result = await agent_workflow.run(sample_context)

        assert result is not None
        assert result["status"] == "completed"
        assert call_count == 4  # Verify that the activity was retried 3 times before succeeding
