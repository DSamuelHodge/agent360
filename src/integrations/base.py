"""
Base integration class for external services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..tools.rest_tool import RESTTool
from ..monitoring.tracing import TracingManager
from ..monitoring.logging import StructuredLogger

class BaseIntegration(ABC):
    """Base class for all external service integrations."""
    
    def __init__(self, api_token: str):
        """Initialize the integration.
        
        Args:
            api_token: Authentication token for the service
        """
        self.api_token = api_token
        self.rest_tool = RESTTool(timeout=30)
        self.logger = StructuredLogger(__name__)
        self.tracer = TracingManager(__name__)
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the service is accessible."""
        pass
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to the service.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            headers: Optional request headers
            data: Optional request body
            params: Optional query parameters
            
        Returns:
            Response data
        """
        with self.tracer.start_span(f"{self.__class__.__name__}._make_request") as span:
            try:
                headers = headers or {}
                headers.update(self._get_auth_headers())
                
                response = await self.rest_tool.execute({
                    "method": method,
                    "url": endpoint,
                    "headers": headers,
                    "data": data,
                    "params": params
                })
                
                if response["status"] >= 400:
                    self.logger.error(
                        "API request failed",
                        extra={
                            "status": response["status"],
                            "endpoint": endpoint,
                            "error": response.get("body", {}).get("message", "Unknown error")
                        }
                    )
                    raise Exception(f"API request failed: {response['status']}")
                
                return response["body"]
                
            except Exception as e:
                self.logger.error(
                    "Request failed",
                    extra={
                        "error": str(e),
                        "endpoint": endpoint
                    }
                )
                raise
    
    @abstractmethod
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for the service."""
        pass
