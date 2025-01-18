"""
Integration tests for memory management and model service.
"""
import pytest
import asyncio
import time
from typing import Dict, Any, List
from src.agent_runtime.orchestrator import Memory, Thought, ThoughtType
from src.agent_runtime.model_service import MockModelService, ModelMetrics
from src.tools.base import ToolRegistry

@pytest.mark.asyncio
async def test_memory_management():
    """Test memory management in orchestrator."""
    memory = Memory(max_short_term_items=3)
    thought = Thought(
        type=ThoughtType.OBSERVATION,
        content="test",
        timestamp=time.time()
    )
    
    # Test memory limits
    memory.add_thought(thought)
    memory.add_thought(Thought(
        type=ThoughtType.THOUGHT,
        content="test2",
        timestamp=time.time()
    ))
    memory.add_thought(Thought(
        type=ThoughtType.ACTION,
        content="test3",
        timestamp=time.time()
    ))
    memory.add_thought(Thought(
        type=ThoughtType.OBSERVATION,
        content="test4",
        timestamp=time.time()
    ))  # Should remove oldest
    
    recent = memory.get_recent_thoughts(2)
    assert len(recent) == 2
    assert recent[-1].content == "test4"
    assert recent[-2].content == "test3"
    
    # Test memory order
    all_thoughts = memory.get_recent_thoughts()
    assert len(all_thoughts) == 3
    assert all_thoughts[0].content == "test2"
    assert all_thoughts[-1].content == "test4"

@pytest.mark.asyncio
async def test_batch_model_invocation():
    """Test batch model invocation."""
    service = MockModelService({"model": "test"})
    prompts = ["test1", "test2", "test3"]
    
    results = await service.batch_invoke(prompts)
    assert len(results) == 3
    assert all(isinstance(r, str) for r in results)
    
    # Test with parameters
    results = await service.batch_invoke(
        prompts,
        parameters={"temperature": 0.7}
    )
    assert len(results) == 3
    
    # Test metrics
    assert service.metrics.total_requests > 0
    assert service.metrics.successful_requests > 0
    assert service.metrics.total_latency >= 0

@pytest.mark.asyncio
async def test_model_error_handling():
    """Test model error handling."""
    service = MockModelService({"model": "test"})
    
    # Test invalid prompt
    with pytest.raises(ValueError):
        await service.invoke("")
    
    # Test metrics after error
    assert service.metrics.failed_requests > 0

@pytest.mark.asyncio
async def test_model_with_different_parameters():
    """Test model with different parameter configurations."""
    service = MockModelService({"model": "test"})
    
    # Test temperature variations
    result1 = await service.invoke("test", {"temperature": 0.1})
    result2 = await service.invoke("test", {"temperature": 0.9})
    assert isinstance(result1, str)
    assert isinstance(result2, str)
    
    # Test max tokens
    result = await service.invoke("test", {"max_tokens": 50})
    assert isinstance(result, str)
    
    # Test with multiple parameters
    result = await service.invoke("test", {
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.9
    })
    assert isinstance(result, str)
