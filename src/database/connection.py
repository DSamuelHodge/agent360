"""
Cassandra connection management for Agent360.
"""

import logging
from typing import Optional, Dict, Any
from cassandra.cluster import (
    Cluster,
    Session,
    ExecutionProfile,
    EXEC_PROFILE_DEFAULT
)
from cassandra.policies import (
    DCAwareRoundRobinPolicy,
    TokenAwarePolicy,
    RetryPolicy,
    ConstantReconnectionPolicy
)
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
from cassandra.cqlengine import connection
from prometheus_client import Counter, Histogram
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Metrics
QUERY_COUNT = Counter(
    'cassandra_queries_total',
    'Total number of Cassandra queries',
    ['operation', 'table']
)
QUERY_LATENCY = Histogram(
    'cassandra_query_latency_seconds',
    'Query latency in seconds',
    ['operation', 'table']
)
ERROR_COUNT = Counter(
    'cassandra_errors_total',
    'Total number of Cassandra errors',
    ['type']
)

class CassandraConnection:
    """Manages Cassandra cluster connections with monitoring."""
    
    def __init__(
        self,
        hosts: list,
        port: int = 9042,
        keyspace: str = 'agent360',
        username: Optional[str] = None,
        password: Optional[str] = None,
        datacenter: Optional[str] = None,
        ssl_context: Optional[Dict[str, Any]] = None
    ):
        """Initialize Cassandra connection.
        
        Args:
            hosts: List of Cassandra hosts
            port: Cassandra port
            keyspace: Default keyspace
            username: Optional username for authentication
            password: Optional password for authentication
            datacenter: Optional datacenter name
            ssl_context: Optional SSL context for secure connections
        """
        self.hosts = hosts
        self.port = port
        self.keyspace = keyspace
        self.datacenter = datacenter
        
        # Create execution profile
        self.profile = ExecutionProfile(
            load_balancing_policy=TokenAwarePolicy(
                DCAwareRoundRobinPolicy(local_dc=datacenter if datacenter else None)
            ),
            retry_policy=RetryPolicy(),
            row_factory=dict_factory
        )
        
        # Configure auth if provided
        auth_provider = None
        if username and password:
            auth_provider = PlainTextAuthProvider(
                username=username,
                password=password
            )
        
        # Create cluster
        self.cluster = Cluster(
            contact_points=hosts,
            port=port,
            auth_provider=auth_provider,
            execution_profiles={
                EXEC_PROFILE_DEFAULT: self.profile
            },
            ssl_context=ssl_context,
            reconnection_policy=ConstantReconnectionPolicy(delay=1.0),
            control_connection_timeout=10.0,
            connect_timeout=10.0
        )
        
        self.session: Optional[Session] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Cassandra cluster."""
        try:
            self.session = self.cluster.connect(self.keyspace)
            
            # Register connection for cqlengine
            connection.register_connection(
                'default',
                session=self.session
            )
            
            logger.info(
                f"Connected to Cassandra cluster: {self.hosts}"
                f" (keyspace: {self.keyspace})"
            )
            
        except Exception as e:
            logger.error(f"Failed to connect to Cassandra: {e}")
            ERROR_COUNT.labels(type='connection').inc()
            raise
    
    async def execute(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> list:
        """Execute a CQL query.
        
        Args:
            query: CQL query string
            parameters: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            List of rows as dictionaries
        """
        with tracer.start_as_current_span('cassandra.query') as span:
            span.set_attribute('db.system', 'cassandra')
            span.set_attribute('db.statement', query)
            
            try:
                # Extract operation and table from query
                operation = query.split()[0].lower()
                table = query.split()[2].split('.')[1] if '.' in query else query.split()[2]
                
                with QUERY_LATENCY.labels(
                    operation=operation,
                    table=table
                ).time():
                    if not self.session:
                        self._connect()
                    
                    result = self.session.execute(
                        query,
                        parameters=parameters or {},
                        timeout=timeout
                    )
                    
                    QUERY_COUNT.labels(
                        operation=operation,
                        table=table
                    ).inc()
                    
                    return list(result)
                
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                ERROR_COUNT.labels(type='query').inc()
                span.record_exception(e)
                raise
    
    def close(self) -> None:
        """Close cluster connection."""
        if self.session:
            self.session.shutdown()
        if self.cluster:
            self.cluster.shutdown()
            
    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
