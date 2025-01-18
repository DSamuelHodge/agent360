import pytest
from src.workflows.patterns_mock import ChainOfThought, ReflectiveExecution
from src.agent_runtime.context_mock import AgentContext, AgentState

@pytest.mark.asyncio
async def test_chain_of_thought_workflow(mock_model_client, mock_redis_service):
    """Test chain of thought workflow pattern."""
    workflow = ChainOfThought(mock_model_client, mock_redis_service)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "gpt-4"},
        tool_config={}
    )
    
    result = await workflow.execute(context)
    assert result["status"] == "success"
    assert "analysis" in result
    assert "tool_result" in result

@pytest.mark.asyncio
async def test_reflective_execution(mock_model_client, mock_redis_service):
    """Test reflective execution workflow pattern."""
    workflow = ReflectiveExecution(mock_model_client, mock_redis_service)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "gpt-4"},
        tool_config={}
    )
    
    result = await workflow.execute(context)
    assert result["status"] == "success"
    assert "reflection" in result
    assert "improved_result" in result

@pytest.mark.asyncio
async def test_workflow_error_handling(mock_model_client, mock_redis_service):
    """Test workflow error handling."""
    workflow = ReflectiveExecution(mock_model_client, mock_redis_service)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "gpt-4"},
        tool_config={"raise_error": True}  # Trigger error condition
    )
    
    try:
        await workflow.execute(context)
        pytest.fail("Expected error was not raised")
    except Exception as e:
        assert "Error handled" in str(e)
        assert workflow.error_count == 1
