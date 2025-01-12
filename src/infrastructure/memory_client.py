"""
Memory client for managing agent memory and knowledge.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import Span
from opentelemetry.trace.status import Status, StatusCode
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Metrics
MEMORY_OPERATIONS = Counter(
    'memory_operations_total',
    'Total number of memory operations',
    ['operation']
)
MEMORY_LATENCY = Histogram(
    'memory_operation_latency_seconds',
    'Memory operation latency in seconds',
    ['operation']
)

class MemoryClient:
    """Client for managing agent memory and knowledge."""
    
    _instance = None
    
    def __init__(self, redis_client, database_client):
        """Initialize memory client.
        
        Args:
            redis_client: Redis client for caching
            database_client: Database client for persistence
        """
        self.redis = redis_client
        self.database = database_client
    
    @classmethod
    async def get_instance(cls) -> 'MemoryClient':
        """Get singleton instance.
        
        Returns:
            MemoryClient instance
        """
        if not cls._instance:
            from .redis_client import RedisClient
            from ..database.connection import DatabaseConnection
            
            redis = await RedisClient.get_instance()
            database = await DatabaseConnection.get_instance()
            cls._instance = cls(redis, database)
        return cls._instance
    
    async def store_memory(
        self,
        agent_id: UUID,
        memory_type: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a memory.
        
        Args:
            agent_id: Agent ID
            memory_type: Type of memory (e.g. 'fact', 'experience')
            content: Memory content
            metadata: Optional metadata
            
        Returns:
            Memory ID
        """
        with tracer.start_as_current_span("memory.store") as span:
            span.set_attribute("agent.id", str(agent_id))
            span.set_attribute("memory.type", memory_type)
            
            try:
                # Generate memory ID
                memory_id = str(UUID())
                
                # Create memory record
                memory = {
                    "id": memory_id,
                    "agent_id": str(agent_id),
                    "type": memory_type,
                    "content": content,
                    "metadata": metadata or {},
                    "created_at": datetime.utcnow().isoformat(),
                }
                
                # Store in database
                query = """
                    INSERT INTO memories (
                        id, agent_id, type, content, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """
                await self.database.execute(
                    query,
                    [
                        memory_id,
                        str(agent_id),
                        memory_type,
                        content,
                        metadata,
                        memory["created_at"],
                    ]
                )
                
                # Cache in Redis
                cache_key = f"memory:{memory_id}"
                await self.redis.set(cache_key, memory)
                
                MEMORY_OPERATIONS.labels(operation="store").inc()
                return memory_id
                
            except Exception as e:
                logger.error(f"Failed to store memory: {e}")
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise
    
    async def get_memory(
        self,
        memory_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a memory by ID.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory if found, None otherwise
        """
        with tracer.start_as_current_span("memory.get") as span:
            span.set_attribute("memory.id", memory_id)
            
            try:
                # Try cache first
                cache_key = f"memory:{memory_id}"
                memory = await self.redis.get(cache_key)
                if memory:
                    return memory
                
                # Query database
                query = "SELECT * FROM memories WHERE id = ?"
                result = await self.database.execute(query, [memory_id])
                row = await result.first()
                
                if not row:
                    return None
                
                # Create memory dict
                memory = {
                    "id": row.id,
                    "agent_id": row.agent_id,
                    "type": row.type,
                    "content": row.content,
                    "metadata": row.metadata,
                    "created_at": row.created_at.isoformat(),
                }
                
                # Cache result
                await self.redis.set(cache_key, memory)
                
                MEMORY_OPERATIONS.labels(operation="get").inc()
                return memory
                
            except Exception as e:
                logger.error(f"Failed to get memory: {e}")
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise
    
    async def search_memories(
        self,
        agent_id: UUID,
        memory_type: Optional[str] = None,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memories.
        
        Args:
            agent_id: Agent ID
            memory_type: Optional memory type filter
            query: Optional search query
            limit: Maximum number of results
            
        Returns:
            List of matching memories
        """
        with tracer.start_as_current_span("memory.search") as span:
            span.set_attribute("agent.id", str(agent_id))
            if memory_type:
                span.set_attribute("memory.type", memory_type)
            
            try:
                # Build query
                query_parts = ["agent_id = ?"]
                params = [str(agent_id)]
                
                if memory_type:
                    query_parts.append("type = ?")
                    params.append(memory_type)
                
                if query:
                    # Add query conditions
                    for key, value in query.items():
                        query_parts.append(f"{key} = ?")
                        params.append(value)
                
                # Execute search
                sql = f"""
                    SELECT * FROM memories 
                    WHERE {' AND '.join(query_parts)}
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                params.append(limit)
                
                result = await self.database.execute(sql, params)
                rows = await result.fetchall()
                
                # Convert to list of dicts
                memories = []
                for row in rows:
                    memory = {
                        "id": row.id,
                        "agent_id": row.agent_id,
                        "type": row.type,
                        "content": row.content,
                        "metadata": row.metadata,
                        "created_at": row.created_at.isoformat(),
                    }
                    memories.append(memory)
                
                MEMORY_OPERATIONS.labels(operation="search").inc()
                return memories
                
            except Exception as e:
                logger.error(f"Failed to search memories: {e}")
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise
