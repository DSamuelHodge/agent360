"""
Additional database tools for Agent360.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

from cassandra.cluster import Session
from cassandra.query import SimpleStatement
from opentelemetry import trace
from prometheus_client import Counter, Histogram

from .connection import CassandraConnection
from .schema import (
    ModelMetrics, AgentSkill, DataCache,
    ResourceUsage, Integration
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class CacheManager:
    """Manages data caching in Cassandra."""
    
    def __init__(self, connection: CassandraConnection):
        self.connection = connection
    
    async def get(self, key: str, tenant_id: str) -> Optional[str]:
        """Get cached value."""
        now = datetime.utcnow()
        result = await self.connection.execute(
            "SELECT value, expires_at FROM data_cache WHERE key = %s AND tenant_id = %s",
            parameters={'key': key, 'tenant_id': tenant_id}
        )
        
        if not result:
            return None
            
        row = result[0]
        if row['expires_at'] and row['expires_at'] < now:
            await self.delete(key, tenant_id)
            return None
            
        await self.connection.execute(
            """
            UPDATE data_cache 
            SET last_accessed = %s, access_count = access_count + 1 
            WHERE key = %s AND tenant_id = %s
            """,
            parameters={
                'last_accessed': now,
                'key': key,
                'tenant_id': tenant_id
            }
        )
        
        return row['value']
    
    async def set(
        self,
        key: str,
        value: str,
        tenant_id: str,
        ttl_seconds: int = 3600,
        content_type: str = 'text/plain'
    ) -> None:
        """Set cached value."""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)
        
        await self.connection.execute(
            """
            INSERT INTO data_cache (
                key, tenant_id, value, content_type,
                expires_at, last_accessed, size_bytes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            parameters={
                'key': key,
                'tenant_id': tenant_id,
                'value': value,
                'content_type': content_type,
                'expires_at': expires_at,
                'last_accessed': now,
                'size_bytes': len(value.encode('utf-8'))
            }
        )
    
    async def delete(self, key: str, tenant_id: str) -> None:
        """Delete cached value."""
        await self.connection.execute(
            "DELETE FROM data_cache WHERE key = %s AND tenant_id = %s",
            parameters={'key': key, 'tenant_id': tenant_id}
        )

class MetricsCollector:
    """Collects and stores model metrics."""
    
    def __init__(self, connection: CassandraConnection):
        self.connection = connection
    
    async def record_request(
        self,
        tenant_id: str,
        model_name: str,
        request_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a model request metrics."""
        now = datetime.utcnow()
        
        await self.connection.execute(
            """
            INSERT INTO model_metrics (
                id, tenant_id, timestamp, model_name,
                request_id, prompt_tokens, completion_tokens,
                total_tokens, latency_ms, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            parameters={
                'id': uuid4(),
                'tenant_id': tenant_id,
                'timestamp': now,
                'model_name': model_name,
                'request_id': request_id,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens,
                'latency_ms': latency_ms,
                'metadata': metadata or {}
            }
        )
    
    async def record_error(
        self,
        tenant_id: str,
        model_name: str,
        request_id: str,
        error_type: str,
        error_message: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a model error."""
        now = datetime.utcnow()
        
        await self.connection.execute(
            """
            INSERT INTO model_metrics (
                id, tenant_id, timestamp, model_name,
                request_id, error_type, error_message, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            parameters={
                'id': uuid4(),
                'tenant_id': tenant_id,
                'timestamp': now,
                'model_name': model_name,
                'request_id': request_id,
                'error_type': error_type,
                'error_message': error_message,
                'metadata': metadata or {}
            }
        )

class ResourceTracker:
    """Tracks resource usage and quotas."""
    
    def __init__(self, connection: CassandraConnection):
        self.connection = connection
    
    async def record_usage(
        self,
        tenant_id: str,
        resource_type: str,
        usage_amount: float,
        cost: float,
        metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Record resource usage."""
        now = datetime.utcnow()
        
        # Get current quota
        result = await self.connection.execute(
            """
            SELECT quota_limit, quota_used
            FROM resource_usage
            WHERE tenant_id = %s AND resource_type = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            parameters={
                'tenant_id': tenant_id,
                'resource_type': resource_type
            }
        )
        
        quota_limit = result[0]['quota_limit'] if result else 0
        quota_used = result[0]['quota_used'] if result else 0
        new_quota_used = quota_used + usage_amount
        
        await self.connection.execute(
            """
            INSERT INTO resource_usage (
                tenant_id, resource_type, timestamp,
                usage_amount, quota_limit, quota_used,
                cost, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            parameters={
                'tenant_id': tenant_id,
                'resource_type': resource_type,
                'timestamp': now,
                'usage_amount': usage_amount,
                'quota_limit': quota_limit,
                'quota_used': new_quota_used,
                'cost': cost,
                'metadata': metadata or {}
            }
        )
    
    async def set_quota(
        self,
        tenant_id: str,
        resource_type: str,
        quota_limit: float
    ) -> None:
        """Set resource quota limit."""
        now = datetime.utcnow()
        
        await self.connection.execute(
            """
            INSERT INTO resource_usage (
                tenant_id, resource_type, timestamp,
                usage_amount, quota_limit, quota_used,
                cost
            )
            VALUES (%s, %s, %s, 0, %s, 0, 0)
            """,
            parameters={
                'tenant_id': tenant_id,
                'resource_type': resource_type,
                'timestamp': now,
                'quota_limit': quota_limit
            }
        )

class IntegrationManager:
    """Manages external service integrations."""
    
    def __init__(self, connection: CassandraConnection):
        self.connection = connection
    
    async def register_integration(
        self,
        tenant_id: str,
        service_type: str,
        config: Dict[str, str],
        credentials: str
    ) -> UUID:
        """Register a new integration."""
        now = datetime.utcnow()
        integration_id = uuid4()
        
        await self.connection.execute(
            """
            INSERT INTO integrations (
                id, tenant_id, service_type, config,
                credentials, status, health_status,
                last_health_check, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            parameters={
                'id': integration_id,
                'tenant_id': tenant_id,
                'service_type': service_type,
                'config': config,
                'credentials': credentials,
                'status': 'active',
                'health_status': 'unknown',
                'last_health_check': now,
                'created_at': now,
                'updated_at': now
            }
        )
        
        return integration_id
    
    async def update_health(
        self,
        integration_id: UUID,
        tenant_id: str,
        health_status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update integration health status."""
        now = datetime.utcnow()
        
        await self.connection.execute(
            """
            UPDATE integrations
            SET health_status = %s,
                last_health_check = %s,
                updated_at = %s,
                error_count = error_count + %s
            WHERE id = %s AND tenant_id = %s
            """,
            parameters={
                'health_status': health_status,
                'last_health_check': now,
                'updated_at': now,
                'error_count': 1 if health_status == 'unhealthy' else 0,
                'id': integration_id,
                'tenant_id': tenant_id
            }
        )
        
    async def get_integration(
        self,
        integration_id: UUID,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get integration details."""
        result = await self.connection.execute(
            """
            SELECT * FROM integrations
            WHERE id = %s AND tenant_id = %s
            """,
            parameters={
                'id': integration_id,
                'tenant_id': tenant_id
            }
        )
        
        return result[0] if result else None
