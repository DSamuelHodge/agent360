"""
Base Tool implementation for Agent360.
Provides the foundation for all tool implementations.
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ToolMetadata:
    """Metadata for tool registration and management."""
    name: str
    description: str
    version: str
    author: str
    parameters: Dict[str, Any]

class BaseTool(ABC):
    """Base class for all tools."""
    
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
        
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with the given parameters.
        
        Args:
            parameters: Tool execution parameters
            
        Returns:
            Tool execution results
        """
        pass
        
    def record_execution(self, success: bool) -> None:
        """Record tool execution metrics."""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

class MockTool(BaseTool):
    """Mock tool for testing."""
    
    def __init__(self, name: str = "test_tool"):
        super().__init__(ToolMetadata(
            name=name,
            description="Mock tool for testing",
            version="1.0.0",
            author="Test Author",
            parameters={"param1": "str", "param2": "int"}
        ))
        
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the mock tool."""
        self.record_execution(True)
        
        if self.metadata.name == "error_tool":
            self.record_execution(False)
            return {
                "status": "error",
                "error": {
                    "type": "TestError",
                    "message": "Test error",
                    "recovery_attempted": True
                }
            }
            
        return {
            "status": "success",
            "result": f"Mock result from {self.metadata.name}",
            "parameters": parameters
        }

class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        # Register default mock tools for testing
        self.register_tool(MockTool("test_tool"))
        self.register_tool(MockTool("rest_tool"))
        self.register_tool(MockTool("error_tool"))
        
    def register_tool(self, tool: BaseTool) -> None:
        """Register a new tool."""
        self.tools[tool.metadata.name] = tool
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(name)
        
    def list_tools(self) -> Dict[str, ToolMetadata]:
        """List all registered tools."""
        return {name: tool.metadata for name, tool in self.tools.items()}
