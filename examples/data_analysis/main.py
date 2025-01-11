"""
Example data analysis bot implementation using Agent360.
Performs data analysis, visualization, and reporting.
"""
import asyncio
import logging
import pandas as pd
import plotly.express as px
from typing import Dict, Any, List
from src.agent_runtime.orchestrator import Orchestrator
from src.agent_runtime.model_service import ModelServiceFactory
from src.tools.base import ToolRegistry
from src.tools.database_tool import DatabaseTool
from src.tools.rest_tool import RESTTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataAnalysisBot:
    """Example data analysis bot using Agent360."""
    
    def __init__(self, config: Dict[str, Any]):
        # Initialize model service
        self.model_service = ModelServiceFactory.create_model_service(
            "openai",
            {"model": "gpt-4"}
        )
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        
        # Configure tools
        self._setup_tools(config)
        
        # Initialize orchestrator
        self.orchestrator = Orchestrator(
            self.model_service,
            self.tool_registry
        )
        
    def _setup_tools(self, config: Dict[str, Any]):
        """Setup required tools."""
        # Database tool for data access
        db_tool = DatabaseTool(
            config["database_url"],
            config["database_name"]
        )
        self.tool_registry.register_tool(db_tool)
        
        # REST tool for external data sources
        rest_tool = RESTTool()
        self.tool_registry.register_tool(rest_tool)
        
    async def analyze_data(
        self,
        query: str,
        data_source: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze data based on query.
        
        Args:
            query: Analysis question or request
            data_source: Source of data
            parameters: Additional parameters
            
        Returns:
            Analysis results with visualizations
        """
        input_data = {
            "query": query,
            "tools": ["database_tool", "rest_tool"],
            "parameters": {
                "data_source": data_source,
                **parameters
            }
        }
        
        try:
            # Process analysis request
            result = await self.orchestrator.process_step(input_data)
            
            # Generate visualizations
            visualizations = await self._create_visualizations(
                result["data"],
                result.get("visualization_type", "auto")
            )
            
            return {
                "analysis": result["analysis"],
                "visualizations": visualizations,
                "insights": result.get("insights", []),
                "recommendations": result.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}")
            raise
            
    async def _create_visualizations(
        self,
        data: pd.DataFrame,
        viz_type: str
    ) -> List[Dict[str, Any]]:
        """Create visualizations from data."""
        visualizations = []
        
        try:
            if viz_type == "auto" or viz_type == "scatter":
                fig = px.scatter(data, x=data.columns[0], y=data.columns[1])
                visualizations.append({
                    "type": "scatter",
                    "plot": fig.to_json()
                })
                
            if viz_type == "auto" or viz_type == "line":
                fig = px.line(data, x=data.columns[0], y=data.columns[1])
                visualizations.append({
                    "type": "line",
                    "plot": fig.to_json()
                })
                
            if viz_type == "auto" or viz_type == "bar":
                fig = px.bar(data, x=data.columns[0], y=data.columns[1])
                visualizations.append({
                    "type": "bar",
                    "plot": fig.to_json()
                })
                
        except Exception as e:
            logger.error(f"Error creating visualizations: {str(e)}")
            
        return visualizations
        
async def main():
    # Configuration
    config = {
        "database_url": "postgresql://localhost:5432",
        "database_name": "analytics"
    }
    
    # Initialize bot
    bot = DataAnalysisBot(config)
    
    # Example analyses
    analyses = [
        {
            "query": "Analyze sales trends over the last quarter",
            "data_source": "sales_data",
            "parameters": {"timeframe": "last_quarter"}
        },
        {
            "query": "Find correlations between customer age and purchase amount",
            "data_source": "customer_data",
            "parameters": {"metrics": ["age", "purchase_amount"]}
        }
    ]
    
    # Run analyses
    for analysis in analyses:
        try:
            result = await bot.analyze_data(
                analysis["query"],
                analysis["data_source"],
                analysis["parameters"]
            )
            logger.info(f"Analysis result: {result['analysis']}")
            logger.info(f"Found {len(result['insights'])} insights")
        except Exception as e:
            logger.error(f"Failed to analyze data: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
