import pytest
from src.workflows.patterns_mock import ChainOfThought, ReflectiveExecution
from src.agent_runtime.context_mock import AgentContext, AgentState

@pytest.mark.asyncio
async def test_workflow_with_tool_config(model_client, redis_client):
    model_client = await model_client
    redis_client = await anext(redis_client)
    workflow = ChainOfThought(model_client, redis_client)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "gpt-4"},
        tool_config={"max_tokens": 100, "temperature": 0.7}
    )
    
    result = await workflow.execute(context)
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_reflective_execution_max_iterations(model_client, redis_client):
    model_client = await model_client
    redis_client = await anext(redis_client)
    workflow = ReflectiveExecution(model_client, redis_client, max_iterations=5)
    context = AgentContext(
        state=AgentState(tenant_id="test"),
        model_config={"model": "gpt-4"},
        tool_config={}
    )
    
    result = await workflow.execute(context)
    assert result["iterations"] > 0
    assert result["iterations"] <= 5

@pytest.mark.asyncio
async def test_workflow_with_state_tracking(model_client, redis_client):
    model_client = await model_client
    redis_client = await anext(redis_client)
    workflow = ChainOfThought(model_client, redis_client)
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
