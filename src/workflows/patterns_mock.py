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
        # Set the model from the context
        self.model_client.model = context.model_config["model"]
        result = await self.model_client.generate("Test prompt")
        return {
            "status": "success",
            "analysis": result["analysis"],
            "tool_result": result["tool_result"]
        }

class ReflectiveExecution:
    def __init__(self, model_client, redis_client, max_iterations: int = 3):
        self.model_client = model_client
        self.redis_client = redis_client
        self.max_iterations = max_iterations

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        # Set the model from the context
        self.model_client.model = context.model_config["model"]
        result = await self.model_client.generate("Test prompt")
        return {
            "iterations": 1,
            "final_result": result["tool_result"]
        }
