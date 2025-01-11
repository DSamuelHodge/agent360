"""
Audit logging system for Agent360.
Provides comprehensive audit trails for all system operations.
"""
from typing import Dict, Any, Optional
import json
import logging
import uuid
from datetime import datetime
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from pydantic import BaseModel
import asyncio
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditLog(Model):
    """Audit log model for database storage."""
    __keyspace__ = 'agent360'
    __table_name__ = 'audit_logs'
    
    id = columns.UUID(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    timestamp = columns.DateTime(primary_key=True)
    event_type = columns.Text(index=True)
    user_id = columns.Text(index=True)
    resource_type = columns.Text()
    resource_id = columns.Text()
    action = columns.Text()
    status = columns.Text()
    details = columns.Text()
    ip_address = columns.Text()
    user_agent = columns.Text()
    correlation_id = columns.Text(index=True)

class AuditEvent(BaseModel):
    """Schema for audit events."""
    tenant_id: str
    event_type: str
    user_id: str
    resource_type: str
    resource_id: str
    action: str
    status: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None

class AuditLogger:
    """Handles audit logging operations."""
    
    def __init__(self, async_mode: bool = True):
        self.async_mode = async_mode
        self._queue = asyncio.Queue() if async_mode else None
        if async_mode:
            asyncio.create_task(self._process_queue())
            
    async def _process_queue(self):
        """Process queued audit events."""
        while True:
            try:
                event = await self._queue.get()
                await self._write_log(event)
                self._queue.task_done()
            except Exception as e:
                logger.error(f"Error processing audit event: {str(e)}")
                
    async def _write_log(self, event: AuditEvent):
        """Write audit log to database."""
        try:
            AuditLog.create(
                id=uuid.uuid4(),
                tenant_id=event.tenant_id,
                timestamp=datetime.utcnow(),
                event_type=event.event_type,
                user_id=event.user_id,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                action=event.action,
                status=event.status,
                details=json.dumps(event.details),
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                correlation_id=event.correlation_id or str(uuid.uuid4())
            )
        except Exception as e:
            logger.error(f"Error writing audit log: {str(e)}")
            
    async def log_event(self, event: AuditEvent):
        """Log an audit event."""
        if self.async_mode:
            await self._queue.put(event)
        else:
            await self._write_log(event)
            
    def audit(self, event_type: str, resource_type: str, action: str):
        """Decorator for auditing function calls."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract context from args/kwargs
                context = self._extract_context(args, kwargs)
                
                # Create audit event
                event = AuditEvent(
                    tenant_id=context.get("tenant_id", "default"),
                    event_type=event_type,
                    user_id=context.get("user_id", "system"),
                    resource_type=resource_type,
                    resource_id=context.get("resource_id", "unknown"),
                    action=action,
                    status="started",
                    details={
                        "args": str(args),
                        "kwargs": str(kwargs)
                    },
                    ip_address=context.get("ip_address"),
                    user_agent=context.get("user_agent"),
                    correlation_id=context.get("correlation_id")
                )
                
                # Log start
                await self.log_event(event)
                
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Log success
                    event.status = "success"
                    event.details["result"] = str(result)
                    await self.log_event(event)
                    
                    return result
                    
                except Exception as e:
                    # Log failure
                    event.status = "failure"
                    event.details["error"] = str(e)
                    await self.log_event(event)
                    raise
                    
            return wrapper
        return decorator
        
    def _extract_context(self, args: tuple, kwargs: Dict) -> Dict[str, Any]:
        """Extract context from function arguments."""
        context = {}
        
        # Try to find context in common locations
        for arg in args:
            if hasattr(arg, "tenant_id"):
                context["tenant_id"] = arg.tenant_id
            if hasattr(arg, "user_id"):
                context["user_id"] = arg.user_id
                
        # Check kwargs
        context.update({
            "tenant_id": kwargs.get("tenant_id", context.get("tenant_id")),
            "user_id": kwargs.get("user_id", context.get("user_id")),
            "resource_id": kwargs.get("resource_id"),
            "ip_address": kwargs.get("ip_address"),
            "user_agent": kwargs.get("user_agent"),
            "correlation_id": kwargs.get("correlation_id")
        })
        
        return context

# Global audit logger instance
audit_logger = AuditLogger()
