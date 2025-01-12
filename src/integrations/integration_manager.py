"""
Integration Manager for Agent360.
Handles integration lifecycle and configuration.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from opentelemetry import trace
from prometheus_client import Counter, Histogram

from ..database.schema import Integration
from ..database.connection import DatabaseConnection
from ..infrastructure.redis_client import RedisClient

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Metrics
INTEGRATION_OPERATIONS = Counter(
    'integration_operations_total',
    'Total number of integration operations',
    ['integration_type', 'operation', 'status']
)
INTEGRATION_LATENCY = Histogram(
    'integration_latency_seconds',
    'Integration operation latency',
    ['integration_type', 'operation']
)

@dataclass
class IntegrationConfig:
    """Integration configuration."""
    integration_type: str
    config: Dict[str, Any]
    enabled: bool = True
    retry_policy: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 30
    cache_ttl_seconds: int = 3600

class IntegrationManager:
    """Manages integration lifecycle and configuration."""
    
    def __init__(
        self,
        cassandra: DatabaseConnection,
        redis: RedisClient
    ):
        """Initialize integration manager.
        
        Args:
            cassandra: Cassandra connection
            redis: Redis client
        """
        self.cassandra = cassandra
        self.redis = redis
        self._integrations: Dict[str, IntegrationConfig] = {}
        
    async def initialize(self):
        """Initialize integration manager."""
        # Load integrations from database
        query = "SELECT * FROM integrations"
        result = await self.cassandra.execute(query)
        
        for row in result:
            self._integrations[row['integration_type']] = IntegrationConfig(
                integration_type=row['integration_type'],
                config=row['config'],
                enabled=row['enabled'],
                retry_policy=row['retry_policy'],
                timeout_seconds=row['timeout_seconds'],
                cache_ttl_seconds=row['cache_ttl_seconds']
            )
    
    async def get_integration(
        self,
        integration_type: str
    ) -> Optional[IntegrationConfig]:
        """Get integration configuration.
        
        Args:
            integration_type: Integration type
            
        Returns:
            Integration configuration if found
        """
        return self._integrations.get(integration_type)
    
    async def register_integration(
        self,
        integration_type: str,
        config: Dict[str, Any],
        enabled: bool = True,
        retry_policy: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 30,
        cache_ttl_seconds: int = 3600
    ):
        """Register new integration.
        
        Args:
            integration_type: Integration type
            config: Integration configuration
            enabled: Whether integration is enabled
            retry_policy: Retry policy configuration
            timeout_seconds: Operation timeout
            cache_ttl_seconds: Cache TTL
        """
        # Create integration record
        integration = Integration(
            integration_type=integration_type,
            config=config,
            enabled=enabled,
            retry_policy=retry_policy,
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        query = """
            INSERT INTO integrations (
                integration_type,
                config,
                enabled,
                retry_policy,
                timeout_seconds,
                cache_ttl_seconds,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await self.cassandra.execute(
            query,
            (
                integration.integration_type,
                integration.config,
                integration.enabled,
                integration.retry_policy,
                integration.timeout_seconds,
                integration.cache_ttl_seconds,
                integration.created_at
            )
        )
        
        # Update local cache
        self._integrations[integration_type] = IntegrationConfig(
            integration_type=integration_type,
            config=config,
            enabled=enabled,
            retry_policy=retry_policy,
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds
        )
    
    async def update_integration(
        self,
        integration_type: str,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        retry_policy: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        cache_ttl_seconds: Optional[int] = None
    ):
        """Update integration configuration.
        
        Args:
            integration_type: Integration type
            config: New configuration
            enabled: New enabled status
            retry_policy: New retry policy
            timeout_seconds: New timeout
            cache_ttl_seconds: New cache TTL
        """
        integration = self._integrations.get(integration_type)
        if not integration:
            raise ValueError(f"Integration {integration_type} not found")
            
        # Update fields
        if config is not None:
            integration.config.update(config)
        if enabled is not None:
            integration.enabled = enabled
        if retry_policy is not None:
            integration.retry_policy = retry_policy
        if timeout_seconds is not None:
            integration.timeout_seconds = timeout_seconds
        if cache_ttl_seconds is not None:
            integration.cache_ttl_seconds = cache_ttl_seconds
            
        # Update database
        query = """
            UPDATE integrations
            SET config = ?,
                enabled = ?,
                retry_policy = ?,
                timeout_seconds = ?,
                cache_ttl_seconds = ?,
                updated_at = ?
            WHERE integration_type = ?
        """
        await self.cassandra.execute(
            query,
            (
                integration.config,
                integration.enabled,
                integration.retry_policy,
                integration.timeout_seconds,
                integration.cache_ttl_seconds,
                datetime.utcnow(),
                integration_type
            )
        )
    
    async def delete_integration(self, integration_type: str):
        """Delete integration.
        
        Args:
            integration_type: Integration type to delete
        """
        if integration_type not in self._integrations:
            raise ValueError(f"Integration {integration_type} not found")
            
        # Delete from database
        query = "DELETE FROM integrations WHERE integration_type = ?"
        await self.cassandra.execute(query, (integration_type,))
        
        # Remove from local cache
        del self._integrations[integration_type]
    
    async def execute_integration(
        self,
        integration_type: str,
        operation: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute integration operation.
        
        Args:
            integration_type: Integration type
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result
        """
        integration = self._integrations.get(integration_type)
        if not integration:
            raise ValueError(f"Integration {integration_type} not found")
            
        if not integration.enabled:
            raise ValueError(f"Integration {integration_type} is disabled")
        
        # Check cache
        cache_key = f"integration:{integration_type}:{operation}:{hash(str(params))}"
        cached_result = await self.redis.get(cache_key)
        if cached_result:
            INTEGRATION_OPERATIONS.labels(
                integration_type=integration_type,
                operation=operation,
                status='cache_hit'
            ).inc()
            return cached_result
        
        try:
            with INTEGRATION_LATENCY.labels(
                integration_type=integration_type,
                operation=operation
            ).time():
                # Execute operation with timeout
                result = await asyncio.wait_for(
                    self._execute_operation(integration, operation, params),
                    timeout=integration.timeout_seconds
                )
                
            # Cache result
            await self.redis.set(
                cache_key,
                result,
                ttl=integration.cache_ttl_seconds
            )
            
            INTEGRATION_OPERATIONS.labels(
                integration_type=integration_type,
                operation=operation,
                status='success'
            ).inc()
            
            return result
            
        except Exception as e:
            INTEGRATION_OPERATIONS.labels(
                integration_type=integration_type,
                operation=operation,
                status='error'
            ).inc()
            
            logger.error(
                f"Integration operation failed: {integration_type}.{operation}: {e}"
            )
            raise
    
    async def _execute_operation(
        self,
        integration: IntegrationConfig,
        operation: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute integration operation with retry policy.
        
        Args:
            integration: Integration configuration
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result
        """
        if not integration.retry_policy:
            # Execute without retries
            return await self._execute_single_operation(
                integration,
                operation,
                params
            )
            
        retry_count = 0
        last_error = None
        
        while retry_count < integration.retry_policy.get('max_retries', 3):
            try:
                return await self._execute_single_operation(
                    integration,
                    operation,
                    params
                )
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_count < integration.retry_policy.get('max_retries', 3):
                    # Wait before retry
                    delay = integration.retry_policy.get('delay_seconds', 1)
                    await asyncio.sleep(delay * (2 ** (retry_count - 1)))
        
        raise last_error
    
    async def _execute_single_operation(
        self,
        integration: IntegrationConfig,
        operation: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute single integration operation.
        
        Args:
            integration: Integration configuration
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result
        """
        # TODO: Implement actual integration execution
        # This is a placeholder that should be replaced with actual implementation
        await asyncio.sleep(0.1)  # Simulate operation
        return {
            'integration_type': integration.integration_type,
            'operation': operation,
            'params': params,
            'result': 'Operation completed successfully'
        }
