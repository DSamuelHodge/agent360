"""
Example weather bot implementation using Agent360.
"""
from typing import Dict, Any
import asyncio
import logging
from src.agent_runtime.orchestrator import Orchestrator
from src.agent_runtime.model_service import ModelServiceFactory
from src.tools.base import ToolRegistry
from src.tools.rest_tool import RESTTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherBot:
    """Example weather bot using Agent360."""
    
    def __init__(self, api_key: str):
        # Initialize model service
        self.model_service = ModelServiceFactory.create_model_service(
            "openai",
            {"model": "gpt-4"}
        )
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        
        # Configure weather API tool
        weather_tool = RESTTool()
        weather_tool.api_key = api_key
        self.tool_registry.register_tool(weather_tool)
        
        # Initialize orchestrator
        self.orchestrator = Orchestrator(
            self.model_service,
            self.tool_registry
        )
        
    async def get_weather(self, location: str) -> Dict[str, Any]:
        """
        Get weather for a location.
        
        Args:
            location: Location to get weather for
            
        Returns:
            Weather information
        """
        input_data = {
            "query": f"What is the weather in {location}?",
            "tools": ["rest_tool"],
            "parameters": {
                "location": location
            }
        }
        
        try:
            result = await self.orchestrator.process_step(input_data)
            return result["output"]
            
        except Exception as e:
            logger.error(f"Error getting weather: {str(e)}")
            raise

async def main():
    # Initialize bot
    bot = WeatherBot("your-api-key")
    
    # Example locations
    locations = ["London", "New York", "Tokyo"]
    
    # Get weather for each location
    for location in locations:
        try:
            weather = await bot.get_weather(location)
            logger.info(f"Weather in {location}: {weather}")
        except Exception as e:
            logger.error(f"Failed to get weather for {location}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
