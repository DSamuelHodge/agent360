"""
Distributed tracing implementation for Agent360.
Implements OpenTelemetry tracing with correlation.
"""
from typing import Optional, Dict, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class TracingManager:
    """Manager for distributed tracing."""
    
    def __init__(self, service_name: str):
        # Initialize tracer provider
        provider = TracerProvider()
        processor = BatchSpanProcessor(OTLPSpanExporter())
        provider.add_span_processor(processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        self.tracer = trace.get_tracer(service_name)
        self.propagator = TraceContextTextMapPropagator()
        
    def inject_context(self, headers: Dict[str, str]):
        """Inject tracing context into headers."""
        self.propagator.inject(dict.__setitem__, headers)
        return headers
        
    def extract_context(self, headers: Dict[str, str]):
        """Extract tracing context from headers."""
        return self.propagator.extract(dict.__getitem__, headers)
        
    def create_span(self, name: str, context: Optional[Dict[str, Any]] = None):
        """Create a new span."""
        return self.tracer.start_span(
            name=name,
            context=context
        )

def with_tracing(name: Optional[str] = None):
    """Decorator to add tracing to functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(span_name) as span:
                # Add function parameters as span attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.args", str(args))
                span.set_attribute("function.kwargs", str(kwargs))
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("function.status", "success")
                    return result
                    
                except Exception as e:
                    span.set_attribute("function.status", "error")
                    span.set_attribute("error.message", str(e))
                    raise
                    
        return wrapper
    return decorator

# Initialize global tracing manager
tracing = TracingManager('agent360')
