"""
Integration tests for Agent360 workflow.
"""
import pytest
import asyncio
from typing import Dict, Any
from src.agent_runtime.orchestrator import Orchestrator
from src.agent_runtime.model_service import ModelServiceFactory
from src.tools.base import ToolRegistry
from src.monitoring.metrics import metrics

@pytest.fixture
async def orchestrator():
    """Create test orchestrator instance."""
    model_service = ModelServiceFactory.create_model_service(
        "test",
        {"model": "test-model"}
    )
    tool_registry = ToolRegistry()
    orchestrator = Orchestrator(model_service, tool_registry)
    yield orchestrator
    await model_service.cleanup()

@pytest.mark.asyncio
async def test_basic_workflow(orchestrator):
    """Test basic agent workflow execution."""
    input_data = {
        "query": "What is the weather in London?",
        "tools": ["rest_tool"]
    }
    
    result = await orchestrator.process_step(input_data)
    
    assert result is not None
    assert "output" in result
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_tool_execution(orchestrator):
    """Test tool execution within workflow."""
    input_data = {
        "query": "Query the database for user data",
        "tools": ["database_tool"],
        "parameters": {
            "query": "SELECT * FROM users LIMIT 1"
        }
    }
    
    result = await orchestrator.process_step(input_data)
    
    assert result is not None
    assert "tool_results" in result
    assert result["tool_results"]["database_tool"]["status"] == "success"

@pytest.mark.asyncio
async def test_error_recovery(orchestrator):
    """Test error recovery mechanisms."""
    input_data = {
        "query": "Make an invalid request",
        "tools": ["rest_tool"],
        "parameters": {
            "url": "invalid-url"
        }
    }
    
    result = await orchestrator.process_step(input_data)
    
    assert result is not None
    assert result["status"] == "recovered"
    assert "error_details" in result
