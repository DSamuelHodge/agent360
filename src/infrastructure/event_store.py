"""
Event store for workflow event sourcing.
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
EVENT_OPERATIONS = Counter(
    'event_operations_total',
    'Total number of event operations',
    ['operation']
)
EVENT_LATENCY = Histogram(
    'event_operation_latency_seconds',
    'Event operation latency in seconds',
    ['operation']
)

class EventStore:
    """Store for workflow events."""
    
    _instance = None
    
    def __init__(self, database_client):
        """Initialize event store.
        
        Args:
            database_client: Database client for persistence
        """
        self.database = database_client
    
    @classmethod
    async def get_instance(cls) -> 'EventStore':
        """Get singleton instance.
        
        Returns:
            EventStore instance
        """
        if not cls._instance:
            from ..database.connection import DatabaseConnection
            database = await DatabaseConnection.get_instance()
            cls._instance = cls(database)
        return cls._instance
    
    async def store_event(
        self,
        workflow_id: UUID,
        event_type: str,
        event_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a workflow event.
        
        Args:
            workflow_id: Workflow ID
            event_type: Type of event
            event_data: Event data
            metadata: Optional metadata
            
        Returns:
            Event ID
        """
        with tracer.start_as_current_span("event.store") as span:
            span.set_attribute("workflow.id", str(workflow_id))
            span.set_attribute("event.type", event_type)
            
            try:
                # Generate event ID
                event_id = str(UUID())
                
                # Create event record
                event = {
                    "id": event_id,
                    "workflow_id": str(workflow_id),
                    "type": event_type,
                    "data": event_data,
                    "metadata": metadata or {},
                    "created_at": datetime.utcnow().isoformat(),
                }
                
                # Store in database
                query = """
                    INSERT INTO workflow_events (
                        id, workflow_id, type, data, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """
                await self.database.execute(
                    query,
                    [
                        event_id,
                        str(workflow_id),
                        event_type,
                        event_data,
                        metadata,
                        event["created_at"],
                    ]
                )
                
                EVENT_OPERATIONS.labels(operation="store").inc()
                return event_id
                
            except Exception as e:
                logger.error(f"Failed to store event: {e}")
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise
    
    async def get_events(
        self,
        workflow_id: UUID,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get workflow events.
        
        Args:
            workflow_id: Workflow ID
            event_type: Optional event type filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of events
        """
        with tracer.start_as_current_span("event.get") as span:
            span.set_attribute("workflow.id", str(workflow_id))
            if event_type:
                span.set_attribute("event.type", event_type)
            
            try:
                # Build query
                query_parts = ["workflow_id = ?"]
                params = [str(workflow_id)]
                
                if event_type:
                    query_parts.append("type = ?")
                    params.append(event_type)
                
                if start_time:
                    query_parts.append("created_at >= ?")
                    params.append(start_time.isoformat())
                
                if end_time:
                    query_parts.append("created_at <= ?")
                    params.append(end_time.isoformat())
                
                # Execute query
                sql = f"""
                    SELECT * FROM workflow_events 
                    WHERE {' AND '.join(query_parts)}
                    ORDER BY created_at ASC
                """
                
                result = await self.database.execute(sql, params)
                rows = await result.fetchall()
                
                # Convert to list of dicts
                events = []
                for row in rows:
                    event = {
                        "id": row.id,
                        "workflow_id": row.workflow_id,
                        "type": row.type,
                        "data": row.data,
                        "metadata": row.metadata,
                        "created_at": row.created_at.isoformat(),
                    }
                    events.append(event)
                
                EVENT_OPERATIONS.labels(operation="get").inc()
                return events
                
            except Exception as e:
                logger.error(f"Failed to get events: {e}")
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise
