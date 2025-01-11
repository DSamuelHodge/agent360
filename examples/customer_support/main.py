"""
Example customer support bot implementation using Agent360.
"""
from typing import Dict, Any, List
import asyncio
import logging
from src.agent_runtime.orchestrator import Orchestrator
from src.agent_runtime.model_service import ModelServiceFactory
from src.tools.base import ToolRegistry
from src.tools.database_tool import DatabaseTool
from src.tools.rest_tool import RESTTool
from src.tools.rag_tool import RAGTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomerSupportBot:
    """Example customer support bot using Agent360."""
    
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
        # Database tool for customer data
        db_tool = DatabaseTool(
            config["cassandra_hosts"],
            config["cassandra_keyspace"]
        )
        self.tool_registry.register_tool(db_tool)
        
        # REST tool for ticket system
        rest_tool = RESTTool()
        self.tool_registry.register_tool(rest_tool)
        
        # RAG tool for knowledge base
        rag_tool = RAGTool(
            config["cassandra_session"],
            config["cassandra_keyspace"],
            "knowledge_base"
        )
        self.tool_registry.register_tool(rag_tool)
        
    async def handle_query(self, customer_id: str, query: str) -> Dict[str, Any]:
        """
        Handle a customer support query.
        
        Args:
            customer_id: Customer identifier
            query: Customer's question or issue
            
        Returns:
            Response with solution or next steps
        """
        input_data = {
            "query": query,
            "tools": ["database_tool", "rest_tool", "rag_tool"],
            "parameters": {
                "customer_id": customer_id
            }
        }
        
        try:
            # Process query
            result = await self.orchestrator.process_step(input_data)
            
            # Create ticket if needed
            if result.get("create_ticket", False):
                await self._create_ticket(customer_id, query, result)
                
            return {
                "response": result["output"],
                "ticket_id": result.get("ticket_id"),
                "suggested_actions": result.get("suggested_actions", [])
            }
            
        except Exception as e:
            logger.error(f"Error handling query: {str(e)}")
            raise
            
    async def _create_ticket(
        self,
        customer_id: str,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """Create a support ticket."""
        ticket_data = {
            "customer_id": customer_id,
            "query": query,
            "priority": context.get("priority", "medium"),
            "category": context.get("category", "general"),
            "initial_response": context["output"]
        }
        
        result = await self.tool_registry.get_tool("rest_tool").execute({
            "method": "POST",
            "url": "https://api.ticketing.example.com/tickets",
            "data": ticket_data
        })
        
        return result["ticket_id"]
        
async def main():
    # Configuration
    config = {
        "cassandra_hosts": ["localhost"],
        "cassandra_keyspace": "support",
        "cassandra_session": None  # Initialize in production
    }
    
    # Initialize bot
    bot = CustomerSupportBot(config)
    
    # Example queries
    queries = [
        ("cust123", "How do I reset my password?"),
        ("cust456", "My payment failed"),
        ("cust789", "Need to upgrade my plan")
    ]
    
    # Handle queries
    for customer_id, query in queries:
        try:
            response = await bot.handle_query(customer_id, query)
            logger.info(f"Response for {customer_id}: {response}")
        except Exception as e:
            logger.error(f"Failed to handle query for {customer_id}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
