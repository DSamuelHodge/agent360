"""
Integration Manager for Agent360.
Handles integration lifecycle and configuration.
"""
import asyncio
import json
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
        
    def _validate_config(self, config: Any) -> None:
        """Validate integration configuration.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ValueError: If config is invalid
        """
        if not isinstance(config, dict):
            raise ValueError("Invalid config format - must be a dictionary")
            
    def _validate_retry_policy(self, policy: Optional[Dict[str, Any]]) -> None:
        """Validate retry policy configuration.
        
        Args:
            policy: Retry policy to validate
            
        Raises:
            ValueError: If policy is invalid
        """
        if policy is None:
            return
        required = {"max_retries", "delay_seconds"}
        if not isinstance(policy, dict) or not all(k in policy for k in required):
            raise ValueError("Invalid retry policy - must contain max_retries and delay_seconds")
            
    def _validate_timeouts(self, timeout: int, cache_ttl: int) -> None:
        """Validate timeout values.
        
        Args:
            timeout: Operation timeout
            cache_ttl: Cache TTL
            
        Raises:
            ValueError: If timeouts are invalid
        """
        if timeout <= 0:
            raise ValueError("Timeout must be positive")
        if cache_ttl <= 0:
            raise ValueError("Cache TTL must be positive")
            
    async def _clear_integration_cache(self, integration_type: str) -> None:
        """Clear all cached results for an integration.
        
        Args:
            integration_type: Integration type to clear cache for
        """
        pattern = f"integration:{integration_type}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await asyncio.gather(*[self.redis.delete(key) for key in keys])

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
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate inputs
        self._validate_config(config)
        self._validate_retry_policy(retry_policy)
        self._validate_timeouts(timeout_seconds, cache_ttl_seconds)
        
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
            
        Raises:
            ValueError: If integration not found or configuration invalid
        """
        integration = await self.get_integration(integration_type)
        if not integration:
            raise ValueError(f"Integration {integration_type} not found")
            
        # Validate new values
        if config is not None:
            self._validate_config(config)
        if retry_policy is not None:
            self._validate_retry_policy(retry_policy)
        if timeout_seconds is not None or cache_ttl_seconds is not None:
            self._validate_timeouts(
                timeout_seconds or integration.timeout_seconds,
                cache_ttl_seconds or integration.cache_ttl_seconds
            )
            
        # Build update query
        updates = []
        params = []
        if config is not None:
            updates.append("config = ?")
            params.append(config)
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(enabled)
        if retry_policy is not None:
            updates.append("retry_policy = ?")
            params.append(retry_policy)
        if timeout_seconds is not None:
            updates.append("timeout_seconds = ?")
            params.append(timeout_seconds)
        if cache_ttl_seconds is not None:
            updates.append("cache_ttl_seconds = ?")
            params.append(cache_ttl_seconds)
            
        if not updates:
            return
            
        # Update database
        query = f"""
            UPDATE integrations
            SET {', '.join(updates)}
            WHERE integration_type = ?
        """
        params.append(integration_type)
        await self.cassandra.execute(query, params)
        
        # Clear cache
        await self._clear_integration_cache(integration_type)
        
        # Update local cache
        self._integrations[integration_type] = IntegrationConfig(
            integration_type=integration_type,
            config=config if config is not None else integration.config,
            enabled=enabled if enabled is not None else integration.enabled,
            retry_policy=retry_policy if retry_policy is not None else integration.retry_policy,
            timeout_seconds=timeout_seconds if timeout_seconds is not None else integration.timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds if cache_ttl_seconds is not None else integration.cache_ttl_seconds
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
        
        # Clear cache
        await self._clear_integration_cache(integration_type)

    async def execute_integration(
        self,
        integration_type: str,
        operation: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute integration operation.
        
        Args:
            integration_type: Integration type
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result
            
        Raises:
            ValueError: If integration not found or disabled
            TimeoutError: If operation times out
        """
        integration = await self.get_integration(integration_type)
        if not integration:
            raise ValueError(f"Integration {integration_type} not found")
            
        if not integration.enabled:
            raise ValueError(f"Integration {integration_type} is disabled")
            
        # Check cache
        cache_key = f"integration:{integration_type}:{operation}:{str(params)}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
            
        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                self._execute_operation(integration, operation, params),
                timeout=integration.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {integration.timeout_seconds} seconds")
        
        # Cache result
        await self.redis.set(
            cache_key,
            json.dumps(result),
            ex=integration.cache_ttl_seconds
        )
        
        return result

    async def _execute_operation(
        self,
        integration: IntegrationConfig,
        operation: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute integration operation with retry policy.
        
        Args:
            integration: Integration configuration
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result
        """
        retry_policy = integration.retry_policy or {
            "max_retries": 3,
            "delay_seconds": 1
        }
        
        attempt = 0
        max_retries = retry_policy["max_retries"]
        delay = retry_policy["delay_seconds"]
        max_delay = retry_policy.get("max_delay_seconds", 5)
        backoff = retry_policy.get("backoff_factor", 2)
        
        while True:
            try:
                return await self._execute_single_operation(integration, operation, params)
            except Exception as e:
                attempt += 1
                if attempt > max_retries:
                    raise
                    
                # Wait before retry with exponential backoff
                retry_delay = min(delay * (backoff ** (attempt - 1)), max_delay)
                await asyncio.sleep(retry_delay)

    async def _execute_single_operation(
        self,
        integration: IntegrationConfig,
        operation: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
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
