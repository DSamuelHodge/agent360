"""Tests for database connection management."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from cassandra.cluster import Cluster, Session
from cassandra.auth import PlainTextAuthProvider

from src.database.connection import DatabaseConnection, get_connection, MockSession, MockCluster
from src.config import Settings

@pytest.fixture
def mock_settings():
    """Create mock settings."""
    return Settings(
        cassandra_hosts=["localhost"],
        cassandra_port=9042,
        cassandra_keyspace="test_keyspace",
        cassandra_username="test_user",
        cassandra_password="test_pass"
    )

@pytest.fixture
def mock_cluster():
    """Create mock Cassandra cluster."""
    cluster = MagicMock(spec=Cluster)
    session = MagicMock(spec=Session)
    cluster.connect.return_value = session
    return cluster

@pytest.fixture
def mock_session(mock_cluster):
    """Create mock Cassandra session."""
    return mock_cluster.connect.return_value

@pytest.fixture
def db_connection(mock_settings):
    """Create database connection with mock settings."""
    with patch("src.database.connection.get_settings", return_value=mock_settings):
        conn = DatabaseConnection()
        yield conn
        # Clean up
        if conn._session:
            conn._session.shutdown()
        if conn._cluster:
            conn._cluster.shutdown()

@pytest.mark.asyncio
async def test_singleton_pattern():
    """Test that DatabaseConnection is a singleton."""
    conn1 = DatabaseConnection()
    conn2 = DatabaseConnection()
    assert conn1 is conn2
    assert get_connection() is conn1

@pytest.mark.asyncio
async def test_init_offline_mode():
    """Test that connection starts in offline mode."""
    conn = DatabaseConnection()
    assert conn.offline_mode is True
    assert isinstance(conn._session, MockSession)
    assert isinstance(conn._cluster, MockCluster)

@pytest.mark.asyncio
async def test_connect_success(db_connection, mock_cluster, mock_session):
    """Test successful database connection."""
    with patch("src.database.connection.Cluster", return_value=mock_cluster) as cluster_mock:
        mock_session.execute.return_value = []  # Mock keyspace creation
        mock_session.set_keyspace.return_value = None  # Mock set keyspace
        
        await db_connection.connect()
        
        # Should create cluster with correct settings
        cluster_mock.assert_called_once()
        assert db_connection.offline_mode is False
        assert db_connection._session is mock_session
        assert db_connection._cluster is mock_cluster
        mock_cluster.connect.assert_called_once()

@pytest.mark.asyncio
async def test_connect_failure(db_connection):
    """Test database connection failure."""
    with patch("src.database.connection.Cluster", side_effect=Exception("Connection failed")):
        await db_connection.connect()
        assert db_connection.offline_mode is True
        assert isinstance(db_connection._session, MockSession)
        assert isinstance(db_connection._cluster, MockCluster)

@pytest.mark.asyncio
async def test_execute_query_online(db_connection, mock_cluster, mock_session):
    """Test query execution in online mode."""
    expected_result = [{"id": 1, "name": "test"}]
    
    with patch("src.database.connection.Cluster", return_value=mock_cluster):
        mock_session.execute.side_effect = [[], expected_result]  # First for keyspace creation, second for actual query
        mock_session.set_keyspace.return_value = None
        await db_connection.connect()
        
        result = db_connection.execute("SELECT * FROM test")
        assert result == expected_result
        assert mock_session.execute.call_count >= 2  # Called at least twice (keyspace + query)

@pytest.mark.asyncio
async def test_execute_query_offline(db_connection):
    """Test query execution in offline mode."""
    result = db_connection.execute("SELECT * FROM test")
    assert result == []

@pytest.mark.asyncio
async def test_execute_async_query_online(db_connection, mock_cluster, mock_session):
    """Test async query execution in online mode."""
    future = Mock()
    
    with patch("src.database.connection.Cluster", return_value=mock_cluster):
        mock_session.execute.return_value = []  # For keyspace creation
        mock_session.set_keyspace.return_value = None
        mock_session.execute_async.return_value = future
        
        await db_connection.connect()
        
        result = db_connection.execute_async("SELECT * FROM test")
        assert result == future
        mock_session.execute_async.assert_called_once_with("SELECT * FROM test", {})

@pytest.mark.asyncio
async def test_execute_async_query_offline(db_connection):
    """Test async query execution in offline mode."""
    db_connection.offline_mode = True
    db_connection._session = MockSession()
    result = db_connection.execute_async("SELECT * FROM test")
    assert result is None

@pytest.mark.asyncio
async def test_close_connection_online(db_connection, mock_cluster, mock_session):
    """Test closing an online connection."""
    with patch("src.database.connection.Cluster", return_value=mock_cluster):
        mock_session.execute.return_value = []  # For keyspace creation
        mock_session.set_keyspace.return_value = None
        await db_connection.connect()
        
        await db_connection.close()
        mock_session.shutdown.assert_called_once()
        mock_cluster.shutdown.assert_called_once()
        assert db_connection.offline_mode is True
        assert isinstance(db_connection._session, MockSession)
        assert isinstance(db_connection._cluster, MockCluster)

@pytest.mark.asyncio
async def test_close_connection_offline(db_connection):
    """Test closing an offline connection."""
    mock_session = Mock(spec=MockSession)
    mock_cluster = Mock(spec=MockCluster)
    db_connection._session = mock_session
    db_connection._cluster = mock_cluster
    
    await db_connection.close()
    mock_session.shutdown.assert_called_once()
    mock_cluster.shutdown.assert_called_once()
    assert db_connection.offline_mode is True
    assert isinstance(db_connection._session, MockSession)
    assert isinstance(db_connection._cluster, MockCluster)

@pytest.mark.asyncio
async def test_auth_provider_creation(db_connection, mock_cluster):
    """Test auth provider creation when credentials are provided."""
    with patch("src.database.connection.Cluster", return_value=mock_cluster) as cluster_mock:
        mock_session = mock_cluster.connect.return_value
        mock_session.execute.return_value = []  # For keyspace creation
        mock_session.set_keyspace.return_value = None
        
        # Ensure settings have auth credentials
        db_connection.settings.cassandra_username = "test_user"
        db_connection.settings.cassandra_password = "test_pass"
        
        await db_connection.connect()
        
        # Verify Cluster was created with correct auth provider
        cluster_mock.assert_called_once()
        call_args = cluster_mock.call_args
        assert "auth_provider" in call_args.kwargs
        auth_provider = call_args.kwargs["auth_provider"]
        assert isinstance(auth_provider, PlainTextAuthProvider)
        assert auth_provider.username == "test_user"
        assert auth_provider.password == "test_pass"
