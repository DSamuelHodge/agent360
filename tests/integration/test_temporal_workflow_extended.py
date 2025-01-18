"""
Extended integration tests for temporal workflows.
"""
import pytest
import asyncio
import uuid
from typing import Dict, Any
from tests.fixtures.mock_services import MockTemporalService

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_temporal_service():
    return MockTemporalService()

async def test_workflow_cancellation(mock_temporal_service):
    """Test workflow cancellation handling."""
    workflow_id = str(uuid.uuid4())
    
    # Start workflow
    task = asyncio.create_task(
        mock_temporal_service.execute_workflow(
            workflow_id=workflow_id,
            input_data={"test": "data"}
        )
    )
    
    # Cancel workflow
    await asyncio.sleep(0.1)
    await mock_temporal_service.cancel_workflow(workflow_id)
    
    try:
        await task
    except asyncio.CancelledError:
        state = await mock_temporal_service.get_workflow_state(workflow_id)
        assert state["status"] == "cancelled"

async def test_workflow_state_persistence(mock_temporal_service):
    """Test workflow state persistence."""
    workflow_id = str(uuid.uuid4())
    
    # Execute workflow
    result = await mock_temporal_service.execute_workflow(
        workflow_id=workflow_id,
        input_data={"test": "data"}
    )
    assert result["status"] == "success"
    
    # Verify state is persisted
    state = await mock_temporal_service.get_workflow_state(workflow_id)
    assert state["status"] == "success"
    
    # Verify state after some time
    await asyncio.sleep(0.1)
    state = await mock_temporal_service.get_workflow_state(workflow_id)
    assert state["status"] == "success"

async def test_concurrent_workflow_execution(mock_temporal_service):
    """Test concurrent workflow execution."""
    workflow_ids = [str(uuid.uuid4()) for _ in range(3)]
    
    # Start multiple workflows
    tasks = [
        mock_temporal_service.execute_workflow(
            workflow_id=wid,
            input_data={"test": f"data{i}"}
        )
        for i, wid in enumerate(workflow_ids)
    ]
    
    # Wait for all workflows
    results = await asyncio.gather(*tasks)
    
    # Verify all workflows completed
    assert all(r["status"] == "success" for r in results)
    
    # Verify all states
    states = await asyncio.gather(*[
        mock_temporal_service.get_workflow_state(wid)
        for wid in workflow_ids
    ])
    assert all(s["status"] == "success" for s in states)

async def test_tool_registry_integration(mock_temporal_service):
    """Test tool registry integration with workflow."""
    workflow_id = str(uuid.uuid4())
    result = await mock_temporal_service.execute_workflow(
        workflow_id=workflow_id,
        input_data={
            "tools": ["test_tool"],
            "params": {"test": "data"}
        }
    )
    
    assert result["status"] == "success"
    assert result["tool_results"][0]["status"] == "success"
    assert result["tool_results"][0]["result"] == "data"
    
    # Test tool execution result
    state = await mock_temporal_service.get_workflow_state(workflow_id)
    assert state["status"] == "success"
