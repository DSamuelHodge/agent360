"""
Agent runtime context and state management.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from opentelemetry import trace
from prometheus_client import Counter, Histogram

from ..database.connection import DatabaseConnection
from ..infrastructure.redis_client import RedisClient
from ..infrastructure.redpanda_client import RedpandaProducer

tracer = trace.get_tracer(__name__)

# Metrics
STATE_OPERATIONS = Counter(
    'agent_state_operations_total',
    'Total number of state operations',
    ['operation', 'status']
)
STATE_LATENCY = Histogram(
    'agent_state_latency_seconds',
    'State operation latency',
    ['operation']
)

@dataclass
class AgentState:
    """Agent execution state."""
    id: UUID = field(default_factory=uuid4)
    conversation_id: Optional[UUID] = None
    tenant_id: Optional[str] = None
    current_step: str = 'initialized'
    memory: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            'id': str(self.id),
            'conversation_id': str(self.conversation_id) if self.conversation_id else None,
            'tenant_id': self.tenant_id,
            'current_step': self.current_step,
            'memory': self.memory,
            'variables': self.variables,
            'tool_results': self.tool_results,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class AgentContext:
    """Agent execution context."""
    state: AgentState
    model_config: Dict[str, Any]
    tool_config: Dict[str, Any]
    workflow_config: Dict[str, Any]
    tenant_config: Optional[Dict[str, Any]] = None

class StateManager:
    """Manages agent state across infrastructure components."""
    
    def __init__(
        self,
        database: DatabaseConnection,
        redis: RedisClient,
        events: RedpandaProducer
    ):
        """Initialize state manager.
        
        Args:
            database: Database connection
            redis: Redis client
            events: Redpanda event producer
        """
        self.database = database
        self.redis = redis
        self.events = events
    
    async def get_state(self, state_id: UUID) -> Optional[AgentState]:
        """Get agent state.
        
        Args:
            state_id: State ID
            
        Returns:
            Agent state if found
        """
        with STATE_LATENCY.labels('get').time():
            try:
                # Try cache first
                cache_key = f"agent:state:{state_id}"
                cached_state = await self.redis.get(cache_key)
                if cached_state:
                    STATE_OPERATIONS.labels(
                        operation='get',
                        status='cache_hit'
                    ).inc()
                    return AgentState(**cached_state)
                
                # Query database
                query = "SELECT * FROM agent_states WHERE id = ?"
                result = await self.database.execute(query, [str(state_id)])
                row = await result.first()
                
                if not row:
                    STATE_OPERATIONS.labels(
                        operation='get',
                        status='not_found'
                    ).inc()
                    return None
                
                state = AgentState(**row)
                
                # Cache state
                await self.redis.set(
                    cache_key,
                    state.to_dict(),
                    ttl=3600  # 1 hour
                )
                
                STATE_OPERATIONS.labels(
                    operation='get',
                    status='success'
                ).inc()
                
                return state
                
            except Exception as e:
                STATE_OPERATIONS.labels(
                    operation='get',
                    status='error'
                ).inc()
                raise
    
    async def update_state(
        self,
        state: AgentState,
        emit_event: bool = True
    ):
        """Update agent state.
        
        Args:
            state: Agent state to update
            emit_event: Whether to emit state change event
        """
        with STATE_LATENCY.labels('update').time():
            try:
                # Update timestamp
                state.updated_at = datetime.utcnow()
                
                # Update database
                query = """
                    INSERT INTO agent_states (
                        id,
                        conversation_id,
                        tenant_id,
                        current_step,
                        memory,
                        variables,
                        tool_results,
                        error,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                await self.database.execute(
                    query,
                    [
                        str(state.id),
                        str(state.conversation_id) if state.conversation_id else None,
                        state.tenant_id,
                        state.current_step,
                        state.memory,
                        state.variables,
                        state.tool_results,
                        state.error,
                        state.created_at,
                        state.updated_at
                    ]
                )
                
                # Update cache
                cache_key = f"agent:state:{state.id}"
                await self.redis.set(
                    cache_key,
                    state.to_dict(),
                    ttl=3600  # 1 hour
                )
                
                # Emit event
                if emit_event:
                    await self.events.emit(
                        'agent.state.changed',
                        {
                            'state_id': str(state.id),
                            'current_step': state.current_step,
                            'timestamp': state.updated_at.isoformat()
                        }
                    )
                
                STATE_OPERATIONS.labels(
                    operation='update',
                    status='success'
                ).inc()
                
            except Exception as e:
                STATE_OPERATIONS.labels(
                    operation='update',
                    status='error'
                ).inc()
                raise
    
    async def delete_state(self, state_id: UUID):
        """Delete agent state.
        
        Args:
            state_id: State ID to delete
        """
        with STATE_LATENCY.labels('delete').time():
            try:
                # Delete from database
                query = "DELETE FROM agent_states WHERE id = ?"
                await self.database.execute(query, [str(state_id)])
                
                # Delete from cache
                cache_key = f"agent:state:{state_id}"
                await self.redis.delete(cache_key)
                
                # Emit event
                await self.events.emit(
                    'agent.state.deleted',
                    {
                        'state_id': str(state_id),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )
                
                STATE_OPERATIONS.labels(
                    operation='delete',
                    status='success'
                ).inc()
                
            except Exception as e:
                STATE_OPERATIONS.labels(
                    operation='delete',
                    status='error'
                ).inc()
                raise
