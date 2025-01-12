import pytest
from src.workflows.patterns_mock import ChainOfThought, ReflectiveExecution
from src.agent_runtime.context_mock import AgentContext, AgentState

@pytest.mark.asyncio
async def test_chain_of_thought_workflow(model_client, redis_client):
    model_client = await model_client
    redis_client = await anext(redis_client)
    workflow = ChainOfThought(model_client, redis_client)
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
async def test_reflective_execution(model_client, redis_client):
    model_client = await model_client
    redis_client = await anext(redis_client)
    workflow = ReflectiveExecution(model_client, redis_client)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "gpt-4"},
        tool_config={}
    )
    
    result = await workflow.execute(context)
    assert result["iterations"] > 0
    assert "final_result" in result

@pytest.mark.asyncio
async def test_workflow_error_handling(model_client, redis_client):
    model_client = await model_client
    redis_client = await anext(redis_client)
    workflow = ChainOfThought(model_client, redis_client)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "invalid_model"},
        tool_config={}
    )
    
    with pytest.raises(Exception, match="Invalid model configuration"):
        await workflow.execute(context)
