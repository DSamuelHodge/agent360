import pytest
from src.workflows.patterns_mock import ChainOfThought, ReflectiveExecution
from src.agent_runtime.context_mock import AgentContext, AgentState

@pytest.mark.asyncio
async def test_workflow_with_tool_config(mock_model_client, mock_redis_service):
    """Test workflow with tool configuration."""
    workflow = ChainOfThought(mock_model_client, mock_redis_service)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "gpt-4"},
        tool_config={"max_tokens": 100, "temperature": 0.7}
    )
    
    result = await workflow.execute(context)
    assert result["status"] == "success"
    assert result["tool_config"]["max_tokens"] == 100
    assert result["tool_config"]["temperature"] == 0.7

@pytest.mark.asyncio
async def test_reflective_execution_max_iterations(mock_model_client, mock_redis_service):
    """Test reflective execution with max iterations."""
    workflow = ReflectiveExecution(mock_model_client, mock_redis_service, max_iterations=5)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "gpt-4"},
        tool_config={}
    )
    
    result = await workflow.execute(context)
    assert result["iterations"] <= 5
    assert result["status"] == "success"
    assert "final_result" in result

@pytest.mark.asyncio
async def test_workflow_with_state_tracking(mock_model_client, mock_redis_service):
    """Test workflow with state tracking."""
    workflow = ChainOfThought(mock_model_client, mock_redis_service)
    context = AgentContext(
        state=AgentState(
            tenant_id="test",
            workflow_id="test_workflow",
            step_id="step_1"
        ),
        model_config={"model": "gpt-4"},
        tool_config={}
    )
    
    result = await workflow.execute(context)
    assert result["status"] == "success"
    assert result["state"]["workflow_id"] == "test_workflow"
    assert result["state"]["step_id"] == "step_1"
