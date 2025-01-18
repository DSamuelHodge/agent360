"""
Integration tests for Agent360 workflow.
"""
import pytest
import asyncio
import uuid
from typing import Dict, Any, AsyncGenerator
from src.monitoring.metrics import metrics
from tests.fixtures.mock_services import mock_temporal_service

pytestmark = pytest.mark.asyncio

async def test_basic_workflow(mock_temporal_service):
    """Test basic agent workflow execution."""
    workflow_id = str(uuid.uuid4())
    input_data = {
        "query": "What is the weather in London?",
        "tools": ["rest_tool"]
    }
    
    result = await mock_temporal_service.execute_workflow(
        workflow_id=workflow_id,
        input_data=input_data,
        task_queue='test-queue'
    )
    
    assert result is not None
    assert result["status"] == "success"
    assert "output" in result
    assert "tool_results" in result
    assert len(result["tool_results"]) == 1
    assert result["tool_results"][0]["status"] == "success"
    metrics.record_workflow_success("test_basic_workflow")
    
    # Verify workflow state
    state = await mock_temporal_service.get_workflow_state(workflow_id)
    assert state["status"] == "success"

async def test_tool_execution(mock_temporal_service):
    """Test tool execution within workflow."""
    workflow_id = str(uuid.uuid4())
    input_data = {
        "query": "Execute test tool",
        "tools": ["test_tool"]
    }
    
    result = await mock_temporal_service.execute_workflow(
        workflow_id=workflow_id,
        input_data=input_data,
        task_queue='test-queue'
    )
    
    assert result is not None
    assert result["status"] == "success"
    assert "tool_results" in result
    assert len(result["tool_results"]) == 1
    assert result["tool_results"][0]["status"] == "success"
    assert "result" in result["tool_results"][0]
    metrics.record_workflow_success("test_tool_execution")
    
    # Verify workflow state
    state = await mock_temporal_service.get_workflow_state(workflow_id)
    assert state["status"] == "success"

async def test_error_recovery(mock_temporal_service):
    """Test error recovery mechanisms."""
    workflow_id = str(uuid.uuid4())
    input_data = {
        "query": "Trigger error",
        "tools": ["error_tool"]
    }
    
    result = await mock_temporal_service.execute_workflow(
        workflow_id=workflow_id,
        input_data=input_data,
        task_queue='test-queue'
    )
    
    assert result is not None
    assert result["status"] == "error"
    assert "error" in result
    assert result["error"]["recovery_attempted"] is True
    metrics.record_workflow_error("test_error_recovery", "expected_error")
    
    # Verify workflow state
    state = await mock_temporal_service.get_workflow_state(workflow_id)
    assert state["status"] == "error"
