"""Tests for workflow patterns."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.agent_runtime.context import AgentContext, AgentState
from src.agent_runtime.reasoning import ReasoningEngine
from src.infrastructure.event_store import EventStore
from src.workflows.patterns import (
    ChainOfThought,
    ReflectiveExecution,
    ParallelReasoning,
    WorkflowPatterns
)

@pytest.fixture
def mock_reasoning():
    """Mock reasoning engine."""
    mock = AsyncMock(spec=ReasoningEngine)
    mock.reason = AsyncMock()
    mock.reflect = AsyncMock()
    return mock

@pytest.fixture
def mock_event_store():
    """Mock event store."""
    mock = AsyncMock(spec=EventStore)
    mock.store_event = AsyncMock()
    mock.list_workflows = AsyncMock()
    return mock

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

@pytest.mark.asyncio
async def test_chain_of_thought(mock_reasoning, mock_event_store, sample_context):
    """Test chain-of-thought pattern."""
    pattern = ChainOfThought(mock_reasoning)
    
    mock_reasoning.reason.return_value = {
        "id": "test_id",
        "thought": "test thought",
        "response": "test response"
    }
    mock_reasoning.reflect.return_value = {
        "reflection": "test reflection"
    }
    
    result = await pattern.execute(sample_context, "test prompt")
    
    assert result["reasoning"]["thought"] == "test thought"
    assert result["reflection"]["reflection"] == "test reflection"
    assert result["final_answer"] == "test response"
    
    mock_reasoning.reason.assert_called_once()
    mock_reasoning.reflect.assert_called_once()

@pytest.mark.asyncio
async def test_reflective_execution(mock_reasoning, mock_event_store, sample_context):
    """Test reflective execution pattern."""
    pattern = ReflectiveExecution(mock_reasoning)
    
    mock_reasoning.reason.side_effect = [
        {"id": "id1", "response": "initial response"},
        {"id": "id2", "response": "improved response"},
        {"id": "id3", "response": "final response"},
        {"id": "id4", "response": "final response"}  # Extra response for final call
    ]
    mock_reasoning.reflect.side_effect = [
        {"reflection": "reflection 1"},
        {"reflection": "reflection 2"},
        {"reflection": "reflection 3"}
    ]
    
    result = await pattern.execute(sample_context, "test prompt")
    
    assert result["initial_result"]["response"] == "initial response"
    assert len(result["reflections"]) == 3
    assert result["final_result"]["response"] == "final response"
    
    assert mock_reasoning.reason.call_count == 4  # Initial + 3 improvements
    assert mock_reasoning.reflect.call_count == 3

@pytest.mark.asyncio
async def test_parallel_reasoning(mock_reasoning, mock_event_store, sample_context):
    """Test parallel reasoning pattern."""
    async def approach1(context):
        return {"thought": "approach 1", "confidence": 0.7}
    
    async def approach2(context):
        return {"thought": "approach 2", "confidence": 0.8}
    
    pattern = ParallelReasoning(mock_reasoning, [approach1, approach2])
    
    result = await pattern.execute(sample_context, "test prompt")
    
    assert len(result["thoughts"]) == 2
    assert result["confidence"] == 0.75  # Average of 0.7 and 0.8

@pytest.mark.asyncio
async def test_workflow_patterns_factory(mock_reasoning, mock_event_store):
    """Test workflow patterns factory."""
    patterns = WorkflowPatterns(mock_reasoning, mock_event_store)
    
    chain = patterns.chain_of_thought()
    assert isinstance(chain, ChainOfThought)
    
    reflective = patterns.reflective_execution()
    assert isinstance(reflective, ReflectiveExecution)
    
    async def approach(context):
        return {"thought": "test", "confidence": 0.5}
    
    parallel = patterns.parallel_reasoning([approach])
    assert isinstance(parallel, ParallelReasoning)

@pytest.mark.asyncio
async def test_pattern_execution_recording(mock_reasoning, mock_event_store, sample_context):
    """Test pattern execution recording."""
    patterns = WorkflowPatterns(mock_reasoning, mock_event_store)
    workflow_id = uuid4()
    
    await patterns.record_pattern_execution(
        workflow_id=workflow_id,
        pattern_name="test_pattern",
        context=sample_context,
        result={"key": "value"}
    )
    
    mock_event_store.store_event.assert_called_once_with(
        workflow_id=workflow_id,
        event_type="pattern_execution",
        event_data={
            "pattern": "test_pattern",
            "context": {
                "tenant_id": sample_context.state.tenant_id,
                "variables": sample_context.state.variables
            },
            "result": {"key": "value"}
        }
    )
