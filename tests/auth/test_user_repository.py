"""Tests for user repository."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from src.auth.user_repository import UserRepository
from src.database.connection import DatabaseConnection, get_connection

@pytest.fixture
def mock_db():
    """Create mock database connection."""
    return MagicMock(spec=DatabaseConnection)

@pytest.fixture
def user_repo(mock_db):
    """Create user repository with mock db."""
    return UserRepository(mock_db)

@pytest.fixture
def sample_user():
    """Create sample user data."""
    user_id = uuid4()
    now = datetime.utcnow()
    return {
        'id': user_id,
        'username': 'testuser',
        'hashed_password': 'hashedpass123',
        'email': 'test@example.com',
        'tenant_id': 'tenant123',
        'roles': ['user'],
        'created_at': now,
        'updated_at': now,
        'failed_attempts': 0,
        'locked_until': None
    }

@pytest.mark.asyncio
async def test_get_user_by_username_found(user_repo, mock_db, sample_user):
    """Test getting user by username when user exists."""
    mock_db.execute.return_value = [sample_user]
    
    result = await user_repo.get_user_by_username(
        username=sample_user['username'],
        tenant_id=sample_user['tenant_id']
    )
    
    assert result == sample_user
    mock_db.execute.assert_called_once_with(
        "SELECT * FROM users WHERE username = %s AND tenant_id = %s ALLOW FILTERING",
        {'username': sample_user['username'], 'tenant_id': sample_user['tenant_id']}
    )

@pytest.mark.asyncio
async def test_get_user_by_username_not_found(user_repo, mock_db):
    """Test getting user by username when user does not exist."""
    mock_db.execute.return_value = []
    
    result = await user_repo.get_user_by_username(
        username='nonexistent',
        tenant_id='tenant123'
    )
    
    assert result is None
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_by_id_found(user_repo, mock_db, sample_user):
    """Test getting user by ID when user exists."""
    mock_db.execute.return_value = [sample_user]
    
    result = await user_repo.get_user_by_id(sample_user['id'])
    
    assert result == sample_user
    mock_db.execute.assert_called_once_with(
        "SELECT * FROM users WHERE id = %s",
        {'id': sample_user['id']}
    )

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_repo, mock_db):
    """Test getting user by ID when user does not exist."""
    mock_db.execute.return_value = []
    user_id = uuid4()
    
    result = await user_repo.get_user_by_id(user_id)
    
    assert result is None
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_create_user(user_repo, mock_db):
    """Test creating a new user."""
    username = 'newuser'
    hashed_password = 'hashedpass123'
    email = 'new@example.com'
    tenant_id = 'tenant123'
    roles = ['user']
    
    with patch('src.auth.user_repository.uuid4') as mock_uuid4, \
         patch('src.auth.user_repository.datetime') as mock_datetime:
        
        user_id = uuid4()
        mock_uuid4.return_value = user_id
        now = datetime.utcnow()
        mock_datetime.utcnow.return_value = now
        
        result = await user_repo.create_user(
            username=username,
            hashed_password=hashed_password,
            email=email,
            tenant_id=tenant_id,
            roles=roles
        )
        
        expected_user = {
            'id': user_id,
            'username': username,
            'hashed_password': hashed_password,
            'email': email,
            'tenant_id': tenant_id,
            'roles': roles,
            'created_at': now,
            'updated_at': now,
            'failed_attempts': 0,
            'locked_until': None
        }
        
        assert result == expected_user
        mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_update_user(user_repo, mock_db, sample_user):
    """Test updating user data."""
    updates = {
        'email': 'updated@example.com',
        'roles': ['user', 'admin']
    }
    
    with patch('src.auth.user_repository.datetime') as mock_datetime:
        now = datetime.utcnow()
        mock_datetime.utcnow.return_value = now
        
        # Mock get_user_by_id to return updated user
        updated_user = sample_user.copy()
        updated_user.update(updates)
        updated_user['updated_at'] = now
        mock_db.execute.side_effect = [None, [updated_user]]  # First None for UPDATE, then user for SELECT
        
        result = await user_repo.update_user(sample_user['id'], updates)
        
        assert result == updated_user
        assert mock_db.execute.call_count == 2

@pytest.mark.asyncio
async def test_delete_user(user_repo, mock_db):
    """Test deleting a user."""
    user_id = uuid4()
    
    result = await user_repo.delete_user(user_id)
    
    assert result is True
    mock_db.execute.assert_called_once_with(
        "DELETE FROM users WHERE id = %s",
        {'id': user_id}
    )

@pytest.mark.asyncio
async def test_increment_failed_attempts_user_not_found(user_repo, mock_db):
    """Test incrementing failed attempts when user does not exist."""
    mock_db.execute.return_value = []
    
    result = await user_repo.increment_failed_attempts('nonexistent', 'tenant123')
    
    assert result is None
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_increment_failed_attempts_below_limit(user_repo, mock_db, sample_user):
    """Test incrementing failed attempts when below limit."""
    user = sample_user.copy()
    user['failed_attempts'] = 2
    mock_db.execute.side_effect = [[user], None]  # First for get_user, second for update
    
    result = await user_repo.increment_failed_attempts(
        user['username'],
        user['tenant_id']
    )
    
    assert result == 3
    assert mock_db.execute.call_count == 2

@pytest.mark.asyncio
async def test_increment_failed_attempts_reaches_limit(user_repo, mock_db, sample_user):
    """Test incrementing failed attempts when reaching limit."""
    user = sample_user.copy()
    user['failed_attempts'] = 4
    mock_db.execute.side_effect = [[user], None]  # First for get_user, second for update
    
    with patch('src.auth.user_repository.datetime') as mock_datetime:
        now = datetime.utcnow()
        mock_datetime.utcnow.return_value = now
        
        result = await user_repo.increment_failed_attempts(
            user['username'],
            user['tenant_id']
        )
        
        assert result == 5
        assert mock_db.execute.call_count == 2
        # Verify locked_until was set in the update query
        update_call = mock_db.execute.call_args_list[1]
        assert update_call[0][1]['locked_until'] == now + timedelta(minutes=30)

@pytest.mark.asyncio
async def test_reset_failed_attempts_user_not_found(user_repo, mock_db):
    """Test resetting failed attempts when user does not exist."""
    mock_db.execute.return_value = []
    
    result = await user_repo.reset_failed_attempts('nonexistent', 'tenant123')
    
    assert result is False
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_reset_failed_attempts_success(user_repo, mock_db, sample_user):
    """Test resetting failed attempts successfully."""
    user = sample_user.copy()
    user['failed_attempts'] = 3
    user['locked_until'] = datetime.utcnow()
    mock_db.execute.side_effect = [[user], None]  # First for get_user, second for update
    
    with patch('src.auth.user_repository.datetime') as mock_datetime:
        now = datetime.utcnow()
        mock_datetime.utcnow.return_value = now
        
        result = await user_repo.reset_failed_attempts(
            user['username'],
            user['tenant_id']
        )
        
        assert result is True
        assert mock_db.execute.call_count == 2
        # Verify failed_attempts and locked_until were reset in update query
        update_call = mock_db.execute.call_args_list[1]
        assert 'failed_attempts = 0' in update_call[0][0]
        assert 'locked_until = null' in update_call[0][0]
