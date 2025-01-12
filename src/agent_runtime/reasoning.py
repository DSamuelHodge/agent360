"""
Agent reasoning engine and memory management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import Span
from opentelemetry.trace.status import Status, StatusCode
from prometheus_client import Counter, Histogram

from ..infrastructure.model_client import ModelClient
from ..infrastructure.memory_client import MemoryClient

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Metrics
REASONING_OPERATIONS = Counter(
    'reasoning_operations_total',
    'Total number of reasoning operations',
    ['operation']
)
REASONING_LATENCY = Histogram(
    'reasoning_operation_latency_seconds',
    'Reasoning operation latency in seconds',
    ['operation']
)

class Memory:
    """Memory object."""
    
    def __init__(
        self,
        memory_id: str,
        agent_id: UUID,
        memory_type: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None
    ):
        """Initialize memory.
        
        Args:
            memory_id: Memory ID
            agent_id: Agent ID
            memory_type: Type of memory
            content: Memory content
            metadata: Optional metadata
            created_at: Creation timestamp
        """
        self.id = memory_id
        self.agent_id = agent_id
        self.type = memory_type
        self.content = content
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow().isoformat()

class ReasoningEngine:
    """Engine for agent reasoning and memory management."""
    
    def __init__(self, model_client: ModelClient, memory_client: MemoryClient):
        """Initialize reasoning engine.
        
        Args:
            model_client: Model client for LLM inference
            memory_client: Memory client for persistence
        """
        self.model = model_client
        self.memory = memory_client
    
    async def reason(
        self,
        agent_id: UUID,
        context: Dict[str, Any],
        prompt: str
    ) -> Dict[str, Any]:
        """Perform reasoning step.
        
        Args:
            agent_id: Agent ID
            context: Reasoning context
            prompt: Reasoning prompt
            
        Returns:
            Reasoning result
        """
        with tracer.start_as_current_span("reasoning.reason") as span:
            span.set_attribute("agent.id", str(agent_id))
            
            try:
                # Get relevant memories
                memories = await self.memory.search_memories(
                    agent_id=agent_id,
                    limit=5
                )
                
                # Build full context
                full_context = {
                    **context,
                    "memories": memories
                }
                
                # Generate response
                response = await self.model.generate(
                    prompt=prompt,
                    context=full_context
                )
                
                # Store reasoning step
                await self.memory.store_memory(
                    agent_id=agent_id,
                    memory_type="reasoning",
                    content={
                        "prompt": prompt,
                        "context": context,
                        "response": response
                    }
                )
                
                REASONING_OPERATIONS.labels(operation="reason").inc()
                return response
                
            except Exception as e:
                logger.error(f"Reasoning failed: {e}")
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise
    
    async def reflect(
        self,
        agent_id: UUID,
        memories: List[Memory],
        prompt: str
    ) -> Dict[str, Any]:
        """Reflect on memories.
        
        Args:
            agent_id: Agent ID
            memories: List of memories to reflect on
            prompt: Reflection prompt
            
        Returns:
            Reflection result
        """
        with tracer.start_as_current_span("reasoning.reflect") as span:
            span.set_attribute("agent.id", str(agent_id))
            
            try:
                # Build context from memories
                context = {
                    "memories": [
                        {
                            "type": memory.type,
                            "content": memory.content,
                            "created_at": memory.created_at
                        }
                        for memory in memories
                    ]
                }
                
                # Generate reflection
                reflection = await self.model.generate(
                    prompt=prompt,
                    context=context
                )
                
                # Store reflection
                await self.memory.store_memory(
                    agent_id=agent_id,
                    memory_type="reflection",
                    content={
                        "prompt": prompt,
                        "memories": [m.id for m in memories],
                        "reflection": reflection
                    }
                )
                
                REASONING_OPERATIONS.labels(operation="reflect").inc()
                return reflection
                
            except Exception as e:
                logger.error(f"Reflection failed: {e}")
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise
