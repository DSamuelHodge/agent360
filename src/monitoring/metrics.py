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
            ['tool_name', 'status']
        )
        
        self.tool_execution_duration = Histogram(
            'agent360_tool_execution_duration_seconds',
            'Tool execution duration in seconds',
            ['tool_name']
        )
        
        # Model metrics
        self.model_requests_total = Counter(
            'agent360_model_requests_total',
            'Total number of model requests',
            ['model_name', 'status']
        )
        
        self.model_tokens_total = Counter(
            'agent360_model_tokens_total',
            'Total number of tokens processed',
            ['model_name', 'operation']
        )
        
        # System metrics
        self.system_info = Info(
            'agent360_system',
            'System information'
        )
        
    def record_agent_request(self, status: str, duration: float, endpoint: str):
        """Record metrics for an agent request."""
        self.agent_requests_total.labels(status=status).inc()
        self.agent_request_duration.labels(endpoint=endpoint).observe(duration)
        
    def record_tool_execution(self, tool_name: str, status: str, duration: float):
        """Record metrics for a tool execution."""
        self.tool_executions_total.labels(
            tool_name=tool_name,
            status=status
        ).inc()
        self.tool_execution_duration.labels(tool_name=tool_name).observe(duration)
        
    def record_model_request(self, model_name: str, status: str, tokens: int):
        """Record metrics for a model request."""
        self.model_requests_total.labels(
            model_name=model_name,
            status=status
        ).inc()
        self.model_tokens_total.labels(
            model_name=model_name,
            operation='total'
        ).inc(tokens)
        
    def update_system_info(self, info: Dict[str, Any]):
        """Update system information metrics."""
        self.system_info.info(info)
        
    def start_server(self, port: int = 8000):
        """Start the metrics server."""
        try:
            start_http_server(port)
            logger.info(f"Metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {str(e)}")
            raise

# Global metrics collector instance
metrics = MetricsCollector()
