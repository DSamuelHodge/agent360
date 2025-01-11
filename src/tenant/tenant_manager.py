"""
Multi-tenancy support for Agent360.
Implements tenant isolation and management.
"""
from typing import Dict, Any, Optional, List
import logging
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from pydantic import BaseModel
import redis
from datetime import datetime

logger = logging.getLogger(__name__)

class Tenant(Model):
    """Tenant model for database storage."""
    __keyspace__ = 'agent360'
    __table_name__ = 'tenants'
    
    id = columns.UUID(primary_key=True)
    name = columns.Text(required=True)
    status = columns.Text(default='active')
    created_at = columns.DateTime()
    updated_at = columns.DateTime()
    config = columns.Text()  # JSON encoded configuration
    quota = columns.Map(key_type=columns.Text, value_type=columns.Int)

class TenantConfig(BaseModel):
    """Configuration for a tenant."""
    max_requests_per_day: int = 1000
    max_concurrent_requests: int = 10
    allowed_models: List[str] = ["gpt-3.5-turbo", "gpt-4"]
    allowed_tools: List[str] = ["rest_tool", "database_tool"]
    storage_quota_mb: int = 1000
    custom_model_config: Optional[Dict[str, Any]] = None

class TenantManager:
    """Manages multi-tenant operations."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def create_tenant(
        self,
        name: str,
        config: TenantConfig
    ) -> Tenant:
        """Create a new tenant."""
        try:
            tenant = Tenant.create(
                name=name,
                config=config.json(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                quota={
                    "requests": 0,
                    "storage": 0
                }
            )
            
            # Initialize Redis cache
            await self._init_tenant_cache(tenant.id, config)
            
            logger.info(f"Created tenant: {name}")
            return tenant
            
        except Exception as e:
            logger.error(f"Failed to create tenant: {str(e)}")
            raise
            
    async def _init_tenant_cache(self, tenant_id: str, config: TenantConfig):
        """Initialize Redis cache for tenant."""
        key_prefix = f"tenant:{tenant_id}"
        
        pipeline = self.redis.pipeline()
        pipeline.hset(
            f"{key_prefix}:config",
            mapping={
                "max_requests": config.max_requests_per_day,
                "max_concurrent": config.max_concurrent_requests
            }
        )
        pipeline.sadd(f"{key_prefix}:models", *config.allowed_models)
        pipeline.sadd(f"{key_prefix}:tools", *config.allowed_tools)
        pipeline.execute()
        
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return Tenant.objects.filter(id=tenant_id).first()
        
    async def update_tenant(
        self,
        tenant_id: str,
        config: TenantConfig
    ) -> Optional[Tenant]:
        """Update tenant configuration."""
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                return None
                
            # Update tenant
            tenant.config = config.json()
            tenant.updated_at = datetime.utcnow()
            tenant.save()
            
            # Update cache
            await self._init_tenant_cache(tenant_id, config)
            
            return tenant
            
        except Exception as e:
            logger.error(f"Failed to update tenant: {str(e)}")
            raise
            
    async def check_quota(self, tenant_id: str, quota_type: str) -> bool:
        """Check if tenant has available quota."""
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                return False
                
            config = TenantConfig.parse_raw(tenant.config)
            current = tenant.quota.get(quota_type, 0)
            
            if quota_type == "requests":
                return current < config.max_requests_per_day
            elif quota_type == "storage":
                return current < config.storage_quota_mb
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to check quota: {str(e)}")
            return False
            
    async def increment_quota(
        self,
        tenant_id: str,
        quota_type: str,
        amount: int = 1
    ):
        """Increment quota usage."""
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                return
                
            current = tenant.quota.get(quota_type, 0)
            tenant.quota[quota_type] = current + amount
            tenant.save()
            
        except Exception as e:
            logger.error(f"Failed to increment quota: {str(e)}")
            
    async def is_tool_allowed(self, tenant_id: str, tool_name: str) -> bool:
        """Check if tool is allowed for tenant."""
        key = f"tenant:{tenant_id}:tools"
        return self.redis.sismember(key, tool_name)
        
    async def is_model_allowed(self, tenant_id: str, model_name: str) -> bool:
        """Check if model is allowed for tenant."""
        key = f"tenant:{tenant_id}:models"
        return self.redis.sismember(key, model_name)
        
    async def get_tenant_config(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant configuration from cache."""
        key = f"tenant:{tenant_id}:config"
        return self.redis.hgetall(key)
        
class TenantMiddleware:
    """Middleware for tenant isolation."""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        
    async def __call__(self, request, call_next):
        """Process request with tenant isolation."""
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return {"error": "Tenant ID required"}
            
        # Check tenant exists
        tenant = await self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return {"error": "Invalid tenant"}
            
        # Check quota
        if not await self.tenant_manager.check_quota(tenant_id, "requests"):
            return {"error": "Quota exceeded"}
            
        # Add tenant context
        request.state.tenant_id = tenant_id
        
        # Process request
        response = await call_next(request)
        
        # Increment quota
        await self.tenant_manager.increment_quota(tenant_id, "requests")
        
        return response
