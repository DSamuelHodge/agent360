"""
Logging configuration for Agent360.
Implements structured logging with correlation IDs.
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from functools import wraps

# Context variable for request tracking
request_id_ctx = ContextVar('request_id', default=None)
correlation_id_ctx = ContextVar('correlation_id', default=None)

class StructuredLogger:
    """Logger that outputs structured JSON logs."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            
        # Add JSON handler
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)
        
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method."""
        extra = {
            'request_id': request_id_ctx.get(),
            'correlation_id': correlation_id_ctx.get(),
            **kwargs
        }
        self.logger.log(level, message, extra=extra)
        
    def info(self, message: str, **kwargs):
        """Log at INFO level."""
        self._log(logging.INFO, message, **kwargs)
        
    def error(self, message: str, **kwargs):
        """Log at ERROR level."""
        self._log(logging.ERROR, message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log at WARNING level."""
        self._log(logging.WARNING, message, **kwargs)
        
    def debug(self, message: str, **kwargs):
        """Log at DEBUG level."""
        self._log(logging.DEBUG, message, **kwargs)

class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name
        }
        
        # Add extra fields from record
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
            
        return json.dumps(log_data)

def with_logging(func):
    """Decorator to add logging to functions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger = StructuredLogger(__name__)
        
        # Generate request ID if not present
        request_id = request_id_ctx.get()
        if request_id is None:
            request_id = str(uuid.uuid4())
            request_id_ctx.set(request_id)
            
        try:
            logger.info(
                f"Calling {func.__name__}",
                function=func.__name__,
                args=args,
                kwargs=kwargs
            )
            result = await func(*args, **kwargs)
            logger.info(
                f"Completed {func.__name__}",
                function=func.__name__,
                status="success"
            )
            return result
            
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}",
                function=func.__name__,
                error=str(e),
                status="error"
            )
            raise
            
    return wrapper

# Global logger instance
logger = StructuredLogger('agent360')
