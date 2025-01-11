"""
Database Tool implementation for Agent360.
Handles database operations with connection pooling and monitoring.
"""
from typing import Dict, Any, List, Optional
import logging
from cassandra.cluster import Cluster, Session
from cassandra.policies import DCAwareRoundRobinPolicy
from cassandra.pool import HostDistance
from .base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)

class DatabaseTool(BaseTool):
    """Tool for executing database operations with connection pooling."""
    
    def __init__(self, contact_points: List[str], keyspace: str):
        metadata = ToolMetadata(
            name="database_tool",
            description="Execute database operations with connection pooling",
            version="1.0.0",
            author="Agent360",
            parameters={
                "query": "CQL query string",
                "parameters": "Query parameters",
                "consistency_level": "Optional consistency level"
            }
        )
        super().__init__(metadata)
        
        self.cluster = Cluster(
            contact_points=contact_points,
            load_balancing_policy=DCAwareRoundRobinPolicy(),
            protocol_version=4,
            pool_timeout=10
        )
        
        # Configure connection pooling
        self.cluster.set_core_connections_per_host(HostDistance.LOCAL, 10)
        self.cluster.set_max_connections_per_host(HostDistance.LOCAL, 100)
        
        self.keyspace = keyspace
        self._session: Optional[Session] = None
        
    @property
    def session(self) -> Session:
        """Get or create Cassandra session."""
        if self._session is None:
            self._session = self.cluster.connect(self.keyspace)
        return self._session
        
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a database query.
        
        Args:
            parameters: Dictionary containing:
                - query: CQL query string
                - parameters: Query parameters
                - consistency_level: Optional consistency level
                
        Returns:
            Dictionary containing:
                - rows: Query results
                - row_count: Number of rows
                - elapsed: Query duration in ms
        """
        try:
            query = parameters["query"]
            query_params = parameters.get("parameters", {})
            consistency = parameters.get("consistency_level")
            
            # Prepare and execute query
            prepared = self.session.prepare(query)
            if consistency:
                prepared.consistency_level = consistency
                
            result = self.session.execute(prepared, query_params)
            
            response = {
                "rows": list(result),
                "row_count": len(result.current_rows),
                "elapsed": result.response_future.elapsed
            }
            
            self.record_execution(success=True)
            return response
            
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
            self.record_execution(success=False)
            raise
            
    def cleanup(self):
        """Cleanup database connections."""
        if self._session:
            self._session.shutdown()
        if self.cluster:
            self.cluster.shutdown()
