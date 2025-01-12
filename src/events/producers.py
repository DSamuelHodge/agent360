"""
Event producers for Agent360.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from ..infrastructure.redpanda_client import RedpandaClient

class EventProducer:
    """Base event producer."""
    
    def __init__(self, client: RedpandaClient):
        """Initialize event producer.
        
        Args:
            client: Redpanda client instance
        """
        self.client = client
    
    async def _produce_event(
        self,
        topic: str,
        event_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Produce an event to a topic.
        
        Args:
            topic: Topic to produce to
            event_type: Type of event
            data: Event data
            metadata: Optional event metadata
        """
        event = {
            'type': event_type,
            'data': data,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.client.produce(topic, event)

class AgentEventProducer(EventProducer):
    """Producer for agent-related events."""
    
    TOPIC = 'agent-events'
    
    async def task_started(
        self,
        task_id: str,
        agent_id: str,
        task_type: str,
        parameters: Dict[str, Any]
    ) -> None:
        """Produce task started event."""
        await self._produce_event(
            self.TOPIC,
            'task_started',
            {
                'task_id': task_id,
                'agent_id': agent_id,
                'task_type': task_type,
                'parameters': parameters
            }
        )
    
    async def task_completed(
        self,
        task_id: str,
        agent_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Produce task completed event."""
        await self._produce_event(
            self.TOPIC,
            'task_completed',
            {
                'task_id': task_id,
                'agent_id': agent_id,
                'result': result
            }
        )
    
    async def task_failed(
        self,
        task_id: str,
        agent_id: str,
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Produce task failed event."""
        await self._produce_event(
            self.TOPIC,
            'task_failed',
            {
                'task_id': task_id,
                'agent_id': agent_id,
                'error': error,
                'details': details or {}
            }
        )

class SystemEventProducer(EventProducer):
    """Producer for system-related events."""
    
    TOPIC = 'system-events'
    
    async def service_status(
        self,
        service_name: str,
        status: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Produce service status event."""
        await self._produce_event(
            self.TOPIC,
            'service_status',
            {
                'service_name': service_name,
                'status': status,
                'metrics': metrics or {}
            }
        )
    
    async def resource_usage(
        self,
        resource_type: str,
        usage_data: Dict[str, Any]
    ) -> None:
        """Produce resource usage event."""
        await self._produce_event(
            self.TOPIC,
            'resource_usage',
            {
                'resource_type': resource_type,
                'usage_data': usage_data
            }
        )
    
    async def alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Produce alert event."""
        await self._produce_event(
            self.TOPIC,
            'alert',
            {
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                'context': context or {}
            }
        )
