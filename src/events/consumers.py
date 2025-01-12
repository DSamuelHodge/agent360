"""
Event consumers for Agent360.
"""

import logging
from typing import Any, Dict, Optional, List
from ..infrastructure.redpanda_client import RedpandaClient

logger = logging.getLogger(__name__)

class EventConsumer:
    """Base event consumer."""
    
    def __init__(self, client: RedpandaClient, group_id: str):
        """Initialize event consumer.
        
        Args:
            client: Redpanda client instance
            group_id: Consumer group ID
        """
        self.client = client
        self.group_id = group_id
    
    async def start(self, topics: List[str]) -> None:
        """Start consuming events.
        
        Args:
            topics: List of topics to consume from
        """
        await self.client.consume(
            topics=topics,
            handler=self._handle_event,
            group_id=self.group_id
        )
    
    async def _handle_event(
        self,
        topic: str,
        event: Dict[str, Any],
        headers: Optional[Dict[str, str]]
    ) -> None:
        """Handle received event.
        
        Args:
            topic: Topic the event was received from
            event: Event data
            headers: Event headers
        """
        event_type = event.get('type')
        if not event_type:
            logger.warning(f'Received event without type: {event}')
            return
        
        handler = getattr(self, f'handle_{event_type}', None)
        if handler:
            try:
                await handler(event['data'], event.get('metadata', {}))
            except Exception as e:
                logger.error(f'Error handling event {event_type}: {e}')
                raise
        else:
            logger.warning(f'No handler for event type: {event_type}')

class AgentEventConsumer(EventConsumer):
    """Consumer for agent-related events."""
    
    async def handle_task_started(
        self,
        data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Handle task started event."""
        task_id = data['task_id']
        agent_id = data['agent_id']
        logger.info(f'Task {task_id} started by agent {agent_id}')
        # Add your task started handling logic here
    
    async def handle_task_completed(
        self,
        data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Handle task completed event."""
        task_id = data['task_id']
        agent_id = data['agent_id']
        result = data['result']
        logger.info(f'Task {task_id} completed by agent {agent_id}')
        # Add your task completion handling logic here
    
    async def handle_task_failed(
        self,
        data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Handle task failed event."""
        task_id = data['task_id']
        agent_id = data['agent_id']
        error = data['error']
        logger.error(f'Task {task_id} failed by agent {agent_id}: {error}')
        # Add your task failure handling logic here

class SystemEventConsumer(EventConsumer):
    """Consumer for system-related events."""
    
    async def handle_service_status(
        self,
        data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Handle service status event."""
        service_name = data['service_name']
        status = data['status']
        metrics = data.get('metrics', {})
        logger.info(f'Service {service_name} status: {status}')
        # Add your service status handling logic here
    
    async def handle_resource_usage(
        self,
        data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Handle resource usage event."""
        resource_type = data['resource_type']
        usage_data = data['usage_data']
        logger.info(f'Resource usage for {resource_type}: {usage_data}')
        # Add your resource usage handling logic here
    
    async def handle_alert(
        self,
        data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Handle alert event."""
        alert_type = data['alert_type']
        severity = data['severity']
        message = data['message']
        logger.warning(f'{severity} alert - {alert_type}: {message}')
        # Add your alert handling logic here
