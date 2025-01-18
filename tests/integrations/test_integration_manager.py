"""Tests for integration manager."""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
import asyncio
from typing import Dict, Any
import json

from src.integrations.integration_manager import IntegrationManager, IntegrationConfig
from src.database.connection import DatabaseConnection
from src.infrastructure.redis_client import RedisClient

@pytest.fixture
def mock_db():
    """Create mock database connection."""
    mock = AsyncMock(spec=DatabaseConnection)
    mock.execute = AsyncMock()
    return mock

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = AsyncMock(spec=RedisClient)
    mock.get = AsyncMock(return_value=None)  # Default to cache miss
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    mock.keys = AsyncMock(return_value=["key1", "key2"])  # Return some keys
    return mock

@pytest.fixture
def integration_manager(mock_db, mock_redis):
    """Create integration manager with mocks."""
    return IntegrationManager(mock_db, mock_redis)

@pytest.fixture
def sample_integration_config():
    """Create sample integration config."""
    return {
        'integration_type': 'test_integration',
        'config': {'api_key': 'test_key', 'endpoint': 'https://test.com'},
        'enabled': True,
        'retry_policy': {'max_retries': 3, 'delay_seconds': 1},
        'timeout_seconds': 30,
        'cache_ttl_seconds': 3600
    }

@pytest.mark.asyncio
async def test_initialize(integration_manager, mock_db, sample_integration_config):
    """Test initialization of integration manager."""
    # Mock database response
    mock_db.execute.return_value = [sample_integration_config]
    
    await integration_manager.initialize()
    
    # Verify database was queried
    mock_db.execute.assert_called_once_with("SELECT * FROM integrations")
    
    # Verify integration was loaded
    integration = await integration_manager.get_integration(sample_integration_config['integration_type'])
    assert integration is not None
    assert integration.integration_type == sample_integration_config['integration_type']
    assert integration.config == sample_integration_config['config']

@pytest.mark.asyncio
async def test_register_integration(integration_manager, mock_db, sample_integration_config):
    """Test registering a new integration."""
    with patch('src.integrations.integration_manager.datetime') as mock_datetime:
        now = datetime.utcnow()
        mock_datetime.utcnow.return_value = now
        
        await integration_manager.register_integration(
            integration_type=sample_integration_config['integration_type'],
            config=sample_integration_config['config'],
            enabled=sample_integration_config['enabled'],
            retry_policy=sample_integration_config['retry_policy'],
            timeout_seconds=sample_integration_config['timeout_seconds'],
            cache_ttl_seconds=sample_integration_config['cache_ttl_seconds']
        )
        
        # Verify database insert
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args[0]
        assert "INSERT INTO integrations" in call_args[0]
        assert call_args[1][0] == sample_integration_config['integration_type']
        
        # Verify integration was cached
        integration = await integration_manager.get_integration(sample_integration_config['integration_type'])
        assert integration is not None
        assert integration.integration_type == sample_integration_config['integration_type']
        assert integration.config == sample_integration_config['config']

@pytest.mark.asyncio
async def test_update_integration(integration_manager, mock_db, sample_integration_config):
    """Test updating an existing integration."""
    # Register integration first
    await integration_manager.register_integration(
        integration_type=sample_integration_config['integration_type'],
        config=sample_integration_config['config'],
        enabled=sample_integration_config['enabled'],
        retry_policy=sample_integration_config['retry_policy'],
        timeout_seconds=sample_integration_config['timeout_seconds'],
        cache_ttl_seconds=sample_integration_config['cache_ttl_seconds']
    )
    
    # Update integration
    new_config = {'api_key': 'new_key', 'endpoint': 'https://new.com'}
    with patch('src.integrations.integration_manager.datetime') as mock_datetime:
        now = datetime.utcnow()
        mock_datetime.utcnow.return_value = now
        
        await integration_manager.update_integration(
            integration_type=sample_integration_config['integration_type'],
            config=new_config,
            enabled=False
        )
        
        # Verify database update
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0]
        assert "UPDATE integrations" in call_args[0]
        
        # Verify integration was updated in cache
        integration = await integration_manager.get_integration(sample_integration_config['integration_type'])
        assert integration is not None
        assert integration.config == new_config
        assert integration.enabled is False

@pytest.mark.asyncio
async def test_delete_integration(integration_manager, mock_db, sample_integration_config):
    """Test deleting an integration."""
    # Register integration first
    await integration_manager.register_integration(
        integration_type=sample_integration_config['integration_type'],
        config=sample_integration_config['config']
    )
    
    # Delete integration
    await integration_manager.delete_integration(sample_integration_config['integration_type'])
    
    # Verify database delete
    mock_db.execute.assert_called_with(
        "DELETE FROM integrations WHERE integration_type = ?",
        (sample_integration_config['integration_type'],)
    )
    
    # Verify integration was removed from cache
    integration = await integration_manager.get_integration(sample_integration_config['integration_type'])
    assert integration is None

@pytest.mark.asyncio
async def test_execute_integration_cached(integration_manager, mock_redis, sample_integration_config):
    """Test executing integration operation with cached result."""
    # Register integration
    await integration_manager.register_integration(
        integration_type=sample_integration_config['integration_type'],
        config=sample_integration_config['config']
    )
    
    # Mock cached result
    cached_result = {'cached': 'result'}
    mock_redis.get.return_value = json.dumps(cached_result)  # Return serialized result
    
    # Execute operation
    result = await integration_manager.execute_integration(
        integration_type=sample_integration_config['integration_type'],
        operation='test_op',
        params={'param': 'value'}
    )
    
    assert result == cached_result
    mock_redis.get.assert_called_once()

@pytest.mark.asyncio
async def test_execute_integration_with_retry(integration_manager, mock_redis, sample_integration_config):
    """Test executing integration operation with retry policy."""
    # Register integration with retry policy
    await integration_manager.register_integration(
        integration_type=sample_integration_config['integration_type'],
        config=sample_integration_config['config'],
        retry_policy={'max_retries': 2, 'delay_seconds': 0.1}
    )
    
    # Mock cache miss
    mock_redis.get.return_value = None
    
    # Execute operation
    result = await integration_manager.execute_integration(
        integration_type=sample_integration_config['integration_type'],
        operation='test_op',
        params={'param': 'value'}
    )
    
    assert result['operation'] == 'test_op'
    mock_redis.set.assert_called_once()

@pytest.mark.asyncio
async def test_execute_integration_disabled(integration_manager, sample_integration_config):
    """Test executing operation on disabled integration."""
    # Register disabled integration
    await integration_manager.register_integration(
        integration_type=sample_integration_config['integration_type'],
        config=sample_integration_config['config'],
        enabled=False
    )
    
    with pytest.raises(ValueError, match="is disabled"):
        await integration_manager.execute_integration(
            integration_type=sample_integration_config['integration_type'],
            operation='test_op',
            params={}
        )

@pytest.mark.asyncio
async def test_execute_integration_not_found(integration_manager):
    """Test executing operation on non-existent integration."""
    with pytest.raises(ValueError, match="not found"):
        await integration_manager.execute_integration(
            integration_type='nonexistent',
            operation='test_op',
            params={}
        )

@pytest.mark.asyncio
async def test_execute_integration_timeout(integration_manager, mock_redis, sample_integration_config):
    """Test integration operation timeout."""
    # Register integration with short timeout
    await integration_manager.register_integration(
        integration_type=sample_integration_config['integration_type'],
        config=sample_integration_config['config'],
        timeout_seconds=0.1
    )
    
    # Mock cache miss
    mock_redis.get.return_value = None
    
    # Mock slow operation
    async def slow_operation(*args):
        await asyncio.sleep(0.2)
        return {'success': True}
    
    with patch.object(integration_manager, '_execute_operation') as mock_execute:
        mock_execute.side_effect = slow_operation
        with pytest.raises(asyncio.TimeoutError):
            await integration_manager.execute_integration(
                integration_type=sample_integration_config['integration_type'],
                operation='test_op',
                params={}
            )

@pytest.mark.asyncio
async def test_update_integration_not_found(integration_manager):
    """Test updating non-existent integration."""
    with pytest.raises(ValueError, match="not found"):
        await integration_manager.update_integration(
            integration_type='nonexistent',
            config={'new': 'config'}
        )

@pytest.mark.asyncio
async def test_delete_integration_not_found(integration_manager):
    """Test deleting non-existent integration."""
    with pytest.raises(ValueError, match="not found"):
        await integration_manager.delete_integration('nonexistent')

@pytest.mark.asyncio
async def test_register_integration_invalid_config(integration_manager):
    """Test registering integration with invalid config."""
    with pytest.raises(ValueError, match="Invalid config format"):
        await integration_manager.register_integration(
            integration_type="test",
            config="not_a_dict"  # Should be dict
        )

@pytest.mark.asyncio
async def test_register_integration_invalid_retry_policy(integration_manager):
    """Test registering integration with invalid retry policy."""
    with pytest.raises(ValueError, match="Invalid retry policy"):
        await integration_manager.register_integration(
            integration_type="test",
            config={"key": "value"},
            retry_policy={"invalid": "policy"}  # Missing required fields
        )

@pytest.mark.asyncio
async def test_register_integration_invalid_timeouts(integration_manager):
    """Test registering integration with invalid timeouts."""
    with pytest.raises(ValueError, match="Timeout must be positive"):
        await integration_manager.register_integration(
            integration_type="test",
            config={"key": "value"},
            timeout_seconds=-1
        )
    
    with pytest.raises(ValueError, match="Cache TTL must be positive"):
        await integration_manager.register_integration(
            integration_type="test",
            config={"key": "value"},
            cache_ttl_seconds=-1
        )

@pytest.mark.asyncio
async def test_execute_integration_retry_behavior(integration_manager, mock_redis):
    """Test detailed retry behavior."""
    # Register integration with retry policy
    await integration_manager.register_integration(
        integration_type="test",
        config={"key": "value"},
        retry_policy={
            "max_retries": 2,
            "delay_seconds": 0.1,
            "max_delay_seconds": 0.5,
            "backoff_factor": 2
        }
    )
    
    # Mock operation that fails twice then succeeds
    attempt = 0
    async def mock_operation(*args, **kwargs):
        nonlocal attempt
        attempt += 1
        if attempt <= 2:
            raise ValueError(f"Attempt {attempt} failed")
        return {"success": True}
        
    with patch.object(integration_manager, '_execute_single_operation', side_effect=mock_operation):
        result = await integration_manager.execute_integration(
            integration_type="test",
            operation="test_op",
            params={}
        )
        
        assert result["success"] is True
        assert attempt == 3  # Two failures + one success

@pytest.mark.asyncio
async def test_cache_invalidation_on_update(integration_manager, mock_redis, sample_integration_config):
    """Test that cache is invalidated when integration is updated."""
    # Register integration
    await integration_manager.register_integration(
        integration_type=sample_integration_config['integration_type'],
        config=sample_integration_config['config']
    )
    
    # Cache some results
    mock_redis.get.return_value = '{"cached": "result"}'
    
    # Update integration
    await integration_manager.update_integration(
        integration_type=sample_integration_config['integration_type'],
        config={"new": "config"}
    )
    
    # Verify cache was cleared
    mock_redis.delete.assert_called()
    
    # Execute should miss cache
    mock_redis.get.return_value = None
    result = await integration_manager.execute_integration(
        integration_type=sample_integration_config['integration_type'],
        operation="test_op",
        params={}
    )
    assert "cached" not in result

@pytest.mark.asyncio
async def test_cache_expiration(integration_manager, mock_redis, sample_integration_config):
    """Test cache expiration behavior."""
    # Register integration with short TTL
    await integration_manager.register_integration(
        integration_type=sample_integration_config['integration_type'],
        config=sample_integration_config['config'],
        cache_ttl_seconds=1
    )
    
    # Cache result
    mock_redis.get.return_value = None
    await integration_manager.execute_integration(
        integration_type=sample_integration_config['integration_type'],
        operation="test_op",
        params={}
    )
    
    # Verify TTL was set
    mock_redis.set.assert_called_once()
    assert mock_redis.set.call_args[1]['ex'] == 1
