"""
Database schema definitions for Agent360.
"""
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)

class User(Model):
    """User model for authentication and authorization."""
    __table_name__ = 'users'
    
    id = columns.UUID(primary_key=True, default=uuid4)
    username = columns.Text(required=True, index=True)
    hashed_password = columns.Text(required=True)
    email = columns.Text(required=True, index=True)
    tenant_id = columns.Text(required=True, index=True)
    roles = columns.List(value_type=columns.Text)
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime(default=datetime.utcnow)
    last_login = columns.DateTime()
    failed_attempts = columns.Integer(default=0)
    locked_until = columns.DateTime()
    
    def __str__(self) -> str:
        return f"User(username={self.username}, tenant={self.tenant_id})"

class AuditLog(Model):
    """Audit log for tracking system events."""
    __table_name__ = 'audit_logs'
    
    id = columns.UUID(primary_key=True, default=uuid4)
    event_time = columns.DateTime(primary_key=True, default=datetime.utcnow, clustering_order="DESC")
    event_type = columns.Text(required=True, index=True)
    user_id = columns.UUID(index=True)
    tenant_id = columns.Text(required=True, index=True)
    resource_type = columns.Text()
    resource_id = columns.Text()
    action = columns.Text()
    status = columns.Text()
    details = columns.Text()
    
    def __str__(self) -> str:
        return f"AuditLog(type={self.event_type}, user={self.user_id}, tenant={self.tenant_id})"

class WorkflowExecution(Model):
    """Workflow execution tracking."""
    __table_name__ = 'workflow_executions'
    
    id = columns.UUID(primary_key=True, default=uuid4)
    start_time = columns.DateTime(primary_key=True, default=datetime.utcnow, clustering_order="DESC")
    workflow_type = columns.Text(required=True, index=True)
    user_id = columns.UUID(index=True)
    tenant_id = columns.Text(required=True, index=True)
    status = columns.Text(default="pending")
    input_data = columns.Text()
    output_data = columns.Text()
    error_message = columns.Text()
    completion_time = columns.DateTime()
    execution_time_ms = columns.Integer()
    
    def __str__(self) -> str:
        return f"WorkflowExecution(id={self.id}, type={self.workflow_type}, status={self.status})"

class MetricsLog(Model):
    """Performance and operational metrics."""
    __table_name__ = 'metrics_logs'
    
    id = columns.UUID(primary_key=True, default=uuid4)
    metric_time = columns.DateTime(primary_key=True, default=datetime.utcnow, clustering_order="DESC")
    metric_type = columns.Text(required=True, index=True)
    tenant_id = columns.Text(required=True, index=True)
    value = columns.Double()
    unit = columns.Text()
    tags = columns.Map(key_type=columns.Text, value_type=columns.Text)
    
    def __str__(self) -> str:
        return f"MetricsLog(type={self.metric_type}, value={self.value} {self.unit})"

class RateLimitCounter(Model):
    """Rate limiting counters."""
    __table_name__ = 'rate_limit_counters'
    
    key = columns.Text(primary_key=True)
    window = columns.DateTime(primary_key=True)
    count = columns.Counter()
    
    class Meta:
        counter_updates_enabled = True

class CacheStats(Model):
    """Cache statistics tracking."""
    __table_name__ = 'cache_stats'
    
    cache_key = columns.Text(primary_key=True)
    hits = columns.Counter()
    misses = columns.Counter()
    
    class Meta:
        counter_updates_enabled = True

class DataCache(Model):
    """Data cache tracking."""
    __table_name__ = 'data_cache'
    
    key = columns.Text(primary_key=True)
    hits = columns.Counter()
    misses = columns.Counter()
    
    class Meta:
        counter_updates_enabled = True

class ResourceUsage(Model):
    """Resource usage tracking."""
    __table_name__ = 'resource_usage'
    
    tenant_id = columns.Text(primary_key=True)
    resource_type = columns.Text(primary_key=True)
    used = columns.Counter()
    
    class Meta:
        counter_updates_enabled = True

class ServiceHealth(Model):
    """Service health tracking."""
    __table_name__ = 'service_health'
    
    service_id = columns.Text(primary_key=True)
    error_count = columns.Counter()
    request_count = columns.Counter()
    
    class Meta:
        counter_updates_enabled = True

class IntegrationStats(Model):
    """Integration statistics."""
    __table_name__ = 'integration_stats'
    
    integration_id = columns.Text(primary_key=True)
    success_count = columns.Counter()
    error_count = columns.Counter()
    
    class Meta:
        counter_updates_enabled = True

class Integration(Model):
    """Integration configuration model."""
    __table_name__ = 'integrations'
    
    integration_type = columns.Text(primary_key=True)
    config = columns.Map(key_type=columns.Text, value_type=columns.Text)
    enabled = columns.Boolean(default=True)
    retry_policy = columns.Map(key_type=columns.Text, value_type=columns.Text, default=None)
    timeout_seconds = columns.Integer(default=30)
    cache_ttl_seconds = columns.Integer(default=3600)
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime()
    
    def __str__(self) -> str:
        return f"Integration(type={self.integration_type}, enabled={self.enabled})"

async def setup_schema(hosts: list, port: int = 9042):
    """Set up Cassandra schema.
    
    Args:
        hosts: List of Cassandra hosts
        port: Cassandra port
    """
    try:
        # Import here to avoid circular imports
        from .connection import get_connection
        
        # Get database connection
        db = get_connection()
        await db.connect()
        
        # Create tables if they don't exist
        for model in [
            User, AuditLog, WorkflowExecution, MetricsLog,
            RateLimitCounter, CacheStats, DataCache,
            ResourceUsage, ServiceHealth, IntegrationStats, Integration
        ]:
            db.execute(f"""
                CREATE TABLE IF NOT EXISTS {model.__table_name__} (
                    {', '.join(f'{k} {v}' for k, v in model._columns.items())}
                    PRIMARY KEY ({', '.join(model._primary_keys)})
                )
            """)
            
    except Exception as e:
        logger.error(f"Failed to set up schema: {str(e)}")
        raise
