"""
REST API Tool implementation for Agent360.
Handles external API integrations with monitoring and retry logic.
"""
from typing import Dict, Any, Optional
import aiohttp
import backoff
import logging
from .base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)

class RESTTool(BaseTool):
    """Tool for making REST API calls with monitoring and retry logic."""
    
    def __init__(self, timeout: int = 30):
        metadata = ToolMetadata(
            name="rest_tool",
            description="Execute REST API calls with monitoring and retry logic",
            version="1.0.0",
            author="Agent360",
            parameters={
                "method": "HTTP method (GET, POST, PUT, DELETE)",
                "url": "Target URL",
                "headers": "Optional request headers",
                "data": "Optional request body",
                "params": "Optional query parameters"
            }
        )
        super().__init__(metadata)
        self.timeout = timeout
        self.session = None
        
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, TimeoutError),
        max_tries=3
    )
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a REST API call.
        
        Args:
            parameters: Dictionary containing:
                - method: HTTP method
                - url: Target URL
                - headers: Optional headers
                - data: Optional request body
                - params: Optional query parameters
                
        Returns:
            Dictionary containing:
                - status: HTTP status code
                - headers: Response headers
                - body: Response body
                - elapsed: Request duration in ms
        """
        try:
            await self._ensure_session()
            
            method = parameters["method"].upper()
            url = parameters["url"]
            headers = parameters.get("headers", {})
            data = parameters.get("data")
            params = parameters.get("params")
            
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            ) as response:
                body = await response.json()
                result = {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": body,
                    "elapsed": response.elapsed.total_seconds() * 1000
                }
                
                self.record_execution(success=200 <= response.status < 300)
                return result
                
        except Exception as e:
            logger.error(f"REST API call failed: {str(e)}")
            self.record_execution(success=False)
            raise
            
    async def cleanup(self):
        """Cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
