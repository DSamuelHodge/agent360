"""
Metrics implementation for Agent360.
Provides Prometheus metrics collection and exposure.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import start_http_server
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collector for system-wide metrics."""
    
    def __init__(self):
        # Agent metrics
        self.agent_requests_total = Counter(
            'agent360_requests_total',
            'Total number of agent requests',
            ['status']
        )
        
        self.agent_request_duration = Histogram(
            'agent360_request_duration_seconds',
            'Request duration in seconds',
            ['endpoint']
        )
        
        self.agent_concurrent_tasks = Gauge(
            'agent360_concurrent_tasks',
            'Number of concurrent agent tasks'
        )
        
        # Tool metrics
        self.tool_executions_total = Counter(
            'agent360_tool_executions_total',
            'Total number of tool executions',
            ['tool', 'status']
        )
        
        self.tool_execution_duration = Histogram(
            'agent360_tool_execution_duration_seconds',
            'Tool execution duration in seconds',
            ['tool']
        )
        
        # Workflow metrics
        self.workflow_executions_total = Counter(
            'agent360_workflow_executions_total',
            'Total number of workflow executions',
            ['workflow', 'status']
        )
        
        self.workflow_execution_duration = Histogram(
            'agent360_workflow_execution_duration_seconds',
            'Workflow execution duration in seconds',
            ['workflow']
        )
        
        # System metrics
        self.system_info = Info(
            'agent360_system_info',
            'System information'
        )
        
    def record_workflow_success(self, workflow_name: str) -> None:
        """Record a successful workflow execution."""
        self.workflow_executions_total.labels(
            workflow=workflow_name,
            status="success"
        ).inc()
        
    def record_workflow_error(self, workflow_name: str, error_type: str) -> None:
        """Record a workflow execution error."""
        self.workflow_executions_total.labels(
            workflow=workflow_name,
            status="error"
        ).inc()
        
    def record_tool_execution(self, tool_name: str, success: bool, duration: float) -> None:
        """Record a tool execution."""
        status = "success" if success else "error"
        self.tool_executions_total.labels(
            tool=tool_name,
            status=status
        ).inc()
        self.tool_execution_duration.labels(tool=tool_name).observe(duration)
        
    def record_request(self, endpoint: str, success: bool, duration: float) -> None:
        """Record an API request."""
        status = "success" if success else "error"
        self.agent_requests_total.labels(status=status).inc()
        self.agent_request_duration.labels(endpoint=endpoint).observe(duration)
        
    def update_concurrent_tasks(self, count: int) -> None:
        """Update the number of concurrent tasks."""
        self.agent_concurrent_tasks.set(count)
        
    def set_system_info(self, info: Dict[str, str]) -> None:
        """Set system information."""
        self.system_info.info(info)

# Global metrics collector instance
metrics = MetricsCollector()
