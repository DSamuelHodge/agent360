"""
Telemetry and observability infrastructure.
"""
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from opentelemetry import trace, metrics
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.metrics import Counter, Histogram, UpDownCounter
from prometheus_client import Gauge, Info

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# System Metrics
SYSTEM_INFO = Info(
    'agent_system_info',
    'Agent system information'
)
SYSTEM_UPTIME = Gauge(
    'agent_system_uptime_seconds',
    'System uptime in seconds'
)
ACTIVE_WORKFLOWS = UpDownCounter(
    'agent_active_workflows',
    'Number of active workflows'
)
ACTIVE_AGENTS = UpDownCounter(
    'agent_active_agents',
    'Number of active agents'
)

# Resource Metrics
RESOURCE_USAGE = Histogram(
    'agent_resource_usage',
    'Resource usage metrics',
    ['resource_type']  # cpu, memory, disk, network
)
RESOURCE_LIMITS = Gauge(
    'agent_resource_limits',
    'Resource limits',
    ['resource_type']
)

# Business Metrics
WORKFLOW_COSTS = Counter(
    'agent_workflow_costs_total',
    'Total workflow costs',
    ['workflow_type', 'tenant_id']
)
API_COSTS = Counter(
    'agent_api_costs_total',
    'Total API costs',
    ['api_type', 'tenant_id']
)

class TelemetryManager:
    """Manager for system telemetry and observability."""
    
    def __init__(self):
        """Initialize telemetry manager."""
        self.start_time = datetime.utcnow()
        
        # Initialize system info
        SYSTEM_INFO.info({
            'version': '1.0.0',
            'start_time': self.start_time.isoformat()
        })
    
    def update_uptime(self):
        """Update system uptime metric."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        SYSTEM_UPTIME.set(uptime)
    
    @contextmanager
    def workflow_span(
        self,
        workflow_id: UUID,
        workflow_type: str,
        tenant_id: str
    ):
        """Create trace span for workflow execution.
        
        Args:
            workflow_id: Workflow ID
            workflow_type: Type of workflow
            tenant_id: Tenant ID
        """
        ACTIVE_WORKFLOWS.up()
        
        with tracer.start_as_current_span(
            name=f"workflow_{workflow_type}",
            attributes={
                'workflow.id': str(workflow_id),
                'workflow.type': workflow_type,
                'tenant.id': tenant_id
            }
        ) as span:
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                span.set_status(
                    Status(StatusCode.ERROR),
                    str(e)
                )
                raise
                
            finally:
                ACTIVE_WORKFLOWS.down()
    
    @contextmanager
    def agent_span(
        self,
        agent_id: UUID,
        tenant_id: str,
        parent_span: Optional[Span] = None
    ):
        """Create trace span for agent execution.
        
        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID
            parent_span: Optional parent span
        """
        ACTIVE_AGENTS.up()
        
        context = trace.set_span_in_context(parent_span) if parent_span else None
        
        with tracer.start_span(
            name="agent_execution",
            context=context,
            attributes={
                'agent.id': str(agent_id),
                'tenant.id': tenant_id
            }
        ) as span:
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                span.set_status(
                    Status(StatusCode.ERROR),
                    str(e)
                )
                raise
                
            finally:
                ACTIVE_AGENTS.down()
    
    def record_resource_usage(
        self,
        resource_type: str,
        usage: float
    ):
        """Record resource usage metric.
        
        Args:
            resource_type: Type of resource
            usage: Usage value
        """
        RESOURCE_USAGE.labels(
            resource_type=resource_type
        ).observe(usage)
    
    def set_resource_limit(
        self,
        resource_type: str,
        limit: float
    ):
        """Set resource limit.
        
        Args:
            resource_type: Type of resource
            limit: Limit value
        """
        RESOURCE_LIMITS.labels(
            resource_type=resource_type
        ).set(limit)
    
    def record_workflow_cost(
        self,
        workflow_type: str,
        tenant_id: str,
        cost: float
    ):
        """Record workflow cost.
        
        Args:
            workflow_type: Type of workflow
            tenant_id: Tenant ID
            cost: Cost amount
        """
        WORKFLOW_COSTS.labels(
            workflow_type=workflow_type,
            tenant_id=tenant_id
        ).inc(cost)
    
    def record_api_cost(
        self,
        api_type: str,
        tenant_id: str,
        cost: float
    ):
        """Record API cost.
        
        Args:
            api_type: Type of API
            tenant_id: Tenant ID
            cost: Cost amount
        """
        API_COSTS.labels(
            api_type=api_type,
            tenant_id=tenant_id
        ).inc(cost)

# Singleton instance
telemetry = TelemetryManager()
