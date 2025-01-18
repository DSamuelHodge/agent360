"""Tests for agent workflow."""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

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
    return AgentWorkflow()

@pytest.mark.asyncio
async def test_workflow_retry_policy(agent_workflow, sample_context):
    """Test workflow retry policy."""
    activity_calls = []
    state_attempts = {}

    async def mock_activity(*args, **kwargs):
        activity_fn = args[0]
        activity_args = args[1:]
        
        # Record the activity call
        activity_calls.append(activity_fn.__name__)
        
        if activity_fn.__name__ == 'update_state':
            state = activity_args[0]
            state_key = f"{activity_fn.__name__}_{state.current_step}"
            
            # Initialize attempt counter for this state
            if state_key not in state_attempts:
                state_attempts[state_key] = 1
            else:
                state_attempts[state_key] += 1

            # Fail first 4 attempts for each state
            if state_attempts[state_key] <= 4:
                raise ApplicationError(f"Temporary error (attempt {state_attempts[state_key]} for {state.current_step})")
            return activity_args[0]
        elif activity_fn.__name__ == 'execute_reasoning':
            return {"tool_selection": {"name": "test_tool", "params": {}}}
        elif activity_fn.__name__ == 'execute_tool':
            return {"status": "success", "result": "test result"}
        elif activity_fn.__name__ == 'process_result':
            return {"status": "success", "result": "test result"}
        return activity_args[0]

    mock_execute_activity = AsyncMock(side_effect=mock_activity)

    # Let Temporal handle the retry policy
    with patch('temporalio.workflow.execute_activity', mock_execute_activity):
        result = await agent_workflow.run(sample_context)

        assert result is not None
        assert result["status"] == "completed"
        
        # Check that update_state was called enough times
        update_state_calls = len([x for x in activity_calls if x == 'update_state'])
        assert update_state_calls >= 20, f"Expected at least 20 update_state calls, got {update_state_calls}"
        
        # Verify other activities were called exactly once
        assert activity_calls.count('execute_reasoning') == 1
        assert activity_calls.count('execute_tool') == 1
        assert activity_calls.count('process_result') == 1

        # Verify each state was retried 5 times
        for state_key, attempts in state_attempts.items():
            assert attempts == 5, f"State {state_key} had {attempts} attempts, expected 5"
