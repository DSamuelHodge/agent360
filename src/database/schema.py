"""
Cassandra schema definitions for Agent360.
"""

from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from cassandra.cqlengine.management import sync_table, create_keyspace_simple
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

class BaseModel(Model):
    """Base model with common fields."""
    __abstract__ = True
    __keyspace__ = 'agent360'

class Agent(BaseModel):
    """Agent model for storing agent configurations and state."""
    __table_name__ = 'agents'
    
    id = columns.UUID(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    name = columns.Text(required=True)
    description = columns.Text()
    status = columns.Text(default='active')
    capabilities = columns.List(value_type=columns.Text)
    config = columns.Map(key_type=columns.Text, value_type=columns.Text)
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime()
    last_active = columns.DateTime()
    version = columns.Text()

class Task(BaseModel):
    """Task model for storing agent tasks and their results."""
    __table_name__ = 'tasks'
    
    id = columns.UUID(primary_key=True)
    agent_id = columns.UUID(index=True)
    tenant_id = columns.Text(primary_key=True)
    type = columns.Text(index=True)
    status = columns.Text(index=True)
    priority = columns.Integer(default=0)
    parameters = columns.Map(key_type=columns.Text, value_type=columns.Text)
    result = columns.Text()
    error = columns.Text()
    created_at = columns.DateTime(default=datetime.utcnow)
    started_at = columns.DateTime()
    completed_at = columns.DateTime()
    timeout_at = columns.DateTime()

class Conversation(BaseModel):
    """Model for storing conversation history."""
    __table_name__ = 'conversations'
    
    id = columns.UUID(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    agent_id = columns.UUID(index=True)
    user_id = columns.Text(index=True)
    messages = columns.List(value_type=columns.Map(key_type=columns.Text, value_type=columns.Text))
    metadata = columns.Map(key_type=columns.Text, value_type=columns.Text)
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime()
    status = columns.Text(default='active')

class VectorEmbedding(BaseModel):
    """Model for storing vector embeddings for RAG."""
    __table_name__ = 'vector_embeddings'
    
    id = columns.UUID(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    content_type = columns.Text(index=True)
    content_id = columns.Text(index=True)
    embedding = columns.List(value_type=columns.Float)
    metadata = columns.Map(key_type=columns.Text, value_type=columns.Text)
    created_at = columns.DateTime(default=datetime.utcnow)

class AuditLog(BaseModel):
    """Model for storing audit logs."""
    __table_name__ = 'audit_logs'
    
    id = columns.UUID(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    timestamp = columns.DateTime(primary_key=True, clustering_order='DESC')
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

class Tenant(BaseModel):
    """Model for storing tenant information."""
    __table_name__ = 'tenants'
    
    id = columns.UUID(primary_key=True)
    name = columns.Text(required=True)
    status = columns.Text(default='active')
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime()
    config = columns.Text()
    quota = columns.Map(key_type=columns.Text, value_type=columns.Integer)

class ModelMetrics(BaseModel):
    """Model for storing LLM performance metrics."""
    __table_name__ = 'model_metrics'
    
    id = columns.UUID(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    timestamp = columns.DateTime(primary_key=True, clustering_order='DESC')
    model_name = columns.Text(index=True)
    request_id = columns.Text(index=True)
    prompt_tokens = columns.Integer()
    completion_tokens = columns.Integer()
    total_tokens = columns.Integer()
    latency_ms = columns.Float()
    error_type = columns.Text()
    error_message = columns.Text()
    metadata = columns.Map(key_type=columns.Text, value_type=columns.Text)

class AgentSkill(BaseModel):
    """Model for storing agent skills and capabilities."""
    __table_name__ = 'agent_skills'
    
    id = columns.UUID(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    name = columns.Text(required=True)
    description = columns.Text()
    version = columns.Text()
    parameters = columns.Map(key_type=columns.Text, value_type=columns.Text)
    requirements = columns.List(value_type=columns.Text)
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime()
    status = columns.Text(default='active')
    category = columns.Text(index=True)
    tags = columns.List(value_type=columns.Text)

class DataCache(BaseModel):
    """Model for caching frequently accessed data."""
    __table_name__ = 'data_cache'
    
    key = columns.Text(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    value = columns.Text()
    content_type = columns.Text()
    expires_at = columns.DateTime()
    last_accessed = columns.DateTime()
    access_count = columns.Counter()
    size_bytes = columns.Integer()

class ResourceUsage(BaseModel):
    """Model for tracking resource usage and quotas."""
    __table_name__ = 'resource_usage'
    
    tenant_id = columns.Text(primary_key=True)
    resource_type = columns.Text(primary_key=True)
    timestamp = columns.DateTime(primary_key=True, clustering_order='DESC')
    usage_amount = columns.Float()
    quota_limit = columns.Float()
    quota_used = columns.Float()
    cost = columns.Decimal()
    metadata = columns.Map(key_type=columns.Text, value_type=columns.Text)

class Integration(BaseModel):
    """Model for storing external service integrations."""
    __table_name__ = 'integrations'
    
    id = columns.UUID(primary_key=True)
    tenant_id = columns.Text(primary_key=True)
    service_type = columns.Text(index=True)  # github, jira, slack, etc.
    config = columns.Map(key_type=columns.Text, value_type=columns.Text)
    credentials = columns.Text()  # encrypted
    status = columns.Text(default='active')
    health_status = columns.Text()
    last_health_check = columns.DateTime()
    error_count = columns.Counter()
    created_at = columns.DateTime(default=datetime.utcnow)
    updated_at = columns.DateTime()

class IntegrationLog(BaseModel):
    """Model for storing integration logs."""
    __table_name__ = 'integration_logs'
    
    integration_type = columns.Text(primary_key=True)
    operation = columns.Text(primary_key=True)
    params = columns.Map(key_type=columns.Text, value_type=columns.Text)
    result = columns.Map(key_type=columns.Text, value_type=columns.Text)
    status = columns.Text()
    error = columns.Text()
    duration_ms = columns.Integer()
    created_at = columns.DateTime(primary_key=True, clustering_order='DESC')

def setup_schema(hosts: list, port: int = 9042) -> None:
    """Set up Cassandra schema.
    
    Args:
        hosts: List of Cassandra hosts
        port: Cassandra port
    """
    from cassandra.cqlengine import connection
    from cassandra.cluster import Cluster
    
    # Connect to Cassandra
    cluster = Cluster(hosts, port=port)
    session = cluster.connect()
    
    # Create keyspace if it doesn't exist
    create_keyspace_simple('agent360', replication_factor=3)
    
    # Register connection
    connection.register_connection('default', session=session)
    
    # Sync tables
    sync_table(Agent)
    sync_table(Task)
    sync_table(Conversation)
    sync_table(VectorEmbedding)
    sync_table(AuditLog)
    sync_table(Tenant)
    sync_table(ModelMetrics)
    sync_table(AgentSkill)
    sync_table(DataCache)
    sync_table(ResourceUsage)
    sync_table(Integration)
    sync_table(IntegrationLog)
