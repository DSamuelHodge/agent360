"""Database connection management for Agent360."""
import logging
from typing import Optional, Dict, Any
from cassandra.cluster import Cluster, Session
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import DCAwareRoundRobinPolicy

from ..config import get_settings

logger = logging.getLogger(__name__)

class MockSession:
    """Mock session for offline mode."""
    
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> list:
        """Mock query execution.
        
        Args:
            query: Query to execute
            params: Query parameters
            
        Returns:
            Empty list
        """
        logger.debug(f"Mock execute: {query} with params {params}")
        return []
        
    def execute_async(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Mock async query execution.
        
        Args:
            query: Query to execute
            params: Query parameters
            
        Returns:
            None
        """
        logger.debug(f"Mock execute async: {query} with params {params}")
        return None
        
    def shutdown(self):
        """Mock shutdown."""
        pass

class MockCluster:
    """Mock cluster for offline mode."""
    
    def shutdown(self):
        """Mock shutdown."""
        pass

class DatabaseConnection:
    """Singleton database connection manager."""
    
    _instance = None
    _session: Optional[Session] = None
    _cluster = None
    
    def __new__(cls):
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """Initialize connection manager."""
        if not hasattr(self, 'initialized'):
            self.settings = get_settings()
            self.initialized = True
            self.offline_mode = True
            self._session = MockSession()
            self._cluster = MockCluster()
            
    async def connect(self) -> None:
        """Connect to database."""
        try:
            # Configure auth if credentials provided
            auth_provider = None
            if self.settings.cassandra_username and self.settings.cassandra_password:
                auth_provider = PlainTextAuthProvider(
                    username=self.settings.cassandra_username,
                    password=self.settings.cassandra_password
                )
                
            # Create cluster
            cluster = Cluster(
                contact_points=self.settings.cassandra_hosts,
                port=self.settings.cassandra_port,
                auth_provider=auth_provider,
                load_balancing_policy=DCAwareRoundRobinPolicy(),
                protocol_version=4
            )
            
            # Connect and create keyspace if needed
            session = cluster.connect()
            
            # Create keyspace if it doesn't exist
            session.execute("""
                CREATE KEYSPACE IF NOT EXISTS %s
                WITH replication = {
                    'class': 'SimpleStrategy',
                    'replication_factor': '1'
                }
            """ % self.settings.cassandra_keyspace)
            
            # Use keyspace
            session.set_keyspace(self.settings.cassandra_keyspace)
            
            # Only set cluster and session if connection succeeds
            self._cluster = cluster
            self._session = session
            self.offline_mode = False
            logger.info("Successfully connected to database")
            
        except Exception as e:
            logger.warning(f"Failed to connect to database: {str(e)}")
            logger.warning("Running in offline mode")
            if self._session:
                self._session.shutdown()
            if self._cluster:
                self._cluster.shutdown()
            self.offline_mode = True
            self._session = MockSession()
            self._cluster = MockCluster()
            
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> list:
        """Execute a query.
        
        Args:
            query: Query to execute
            params: Query parameters
            
        Returns:
            Query results
        """
        if self.offline_mode:
            return []
            
        try:
            result = self._session.execute(query, params or {})
            return list(result)
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return []
            
    def execute_async(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Execute a query asynchronously.
        
        Args:
            query: Query to execute
            params: Query parameters
            
        Returns:
            Future for query result
        """
        try:
            if self.offline_mode:
                return None
            return self._session.execute_async(query, params or {})
        except Exception as e:
            logger.error(f"Async query execution failed: {str(e)}")
            return None
            
    def get_session(self) -> Optional[Session]:
        """Get current database session.
        
        Returns:
            Current session
        """
        return self._session
        
    async def close(self):
        """Close database connection."""
        if self._session:
            self._session.shutdown()
            self._session = None
            
        if self._cluster:
            self._cluster.shutdown()
            self._cluster = None
            
        self.offline_mode = True
        self._session = MockSession()
        self._cluster = MockCluster()

_connection = None

def get_connection() -> DatabaseConnection:
    """Get database connection instance.
    
    Returns:
        Singleton database connection instance
    """
    global _connection
    if _connection is None:
        _connection = DatabaseConnection()
    return _connection
