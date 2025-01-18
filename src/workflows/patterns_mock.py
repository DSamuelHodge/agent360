"""
Mock workflow patterns for testing.
"""
from typing import Dict, Any
from ..agent_runtime.context_mock import AgentContext

class ChainOfThought:
    def __init__(self, model_client, redis_client):
        self.model_client = model_client
        self.redis_client = redis_client

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        # Set workflow type for appropriate mock responses
        self.model_client.set_workflow_type("chain_of_thought")
        
        # Set the model from the context
        self.model_client.model = context.model_config["model"]
        
        # Generate response
        result = await self.model_client.generate("Test prompt")
        
        # Return all necessary fields
        return {
            "status": result["status"],
            "output": result["output"],
            "analysis": result["analysis"],
            "tool_result": result["tool_result"],
            "tool_config": result["tool_config"],
            "state": result["state"]
        }

class ReflectiveExecution:
    def __init__(self, model_client, redis_client, max_iterations: int = 3):
        self.model_client = model_client
        self.redis_client = redis_client
        self.max_iterations = max_iterations
        self.error_count = 0

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        # Set workflow type for appropriate mock responses
        self.model_client.set_workflow_type("reflective")
        
        # Set the model from the context
        self.model_client.model = context.model_config["model"]
        
        # Check if we should trigger an error
        if context.tool_config.get("raise_error"):
            self.error_count += 1
            raise Exception("Error handled")
        
        # Generate response
        result = await self.model_client.generate("Test prompt")
        
        # Return all necessary fields
        return {
            "status": result["status"],
            "output": result["output"],
            "iterations": result["iterations"],
            "reflection": result["reflection"],
            "improved_result": result["improved_result"],
            "final_result": result["final_result"],
            "tool_result": result["tool_result"],
            "tool_config": result["tool_config"],
            "state": result["state"]
        }
